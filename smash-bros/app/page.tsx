"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import SmashIntro from "./componant/ui/SmashIntro";
import MeleeButton from "./componant/ui/MeleeButton";
import ShopModal from "./componant/modals/ShopModal";
import InventoryModal from "./componant/modals/InventoryModal";
import UseItemModal from "./componant/modals/UseItemModal";
import TournamentSignupModal from "./componant/modals/TournamentSignupModal";
import DuelsModal from "./componant/modals/DuelsModal";
import TournamentCreateModal from "./componant/modals/TournamentCreateModal";
import ConfirmModal from "./componant/modals/ConfirmModal";
import ProfileModal from "./componant/modals/ProfileModal";
import ShopAdminModal from "./componant/modals/ShopAdminModal";
import CharacterSelectScreen from "./componant/modals/CharacterSelectScreen";
import LeaderboardModal from "./componant/modals/LeaderboardModal";
import AdminUsersModal from "./componant/modals/AdminUsersModal";
import { apiJson, fmt, formatShortDate } from "./lib/utils";
import type {
  Duel,
  Fighter,
  Gage,
  GagePayload,
  InventoryEntry,
  InventoryItem,
  LeaderboardEntry,
  Participant,
  PlayableMatch,
  RawTournament,
  Settings,
  ShopItem,
  Sprite,
  Tournament,
  TournamentFormData,
  User,
  UserStats,
} from "./lib/types";

export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [authChecked, setAuthChecked] = useState(false);

  // "shop" | "inv" | "use" | "signup" | "create" | "confirm" | "profile" | null
  const [modal, setModal] = useState<string | null>(null);
  const [balance, setBalance] = useState<number>(0);
  const [stats, setStats] = useState<UserStats>({
    wins: 0,
    losses: 0,
    tournaments: 0,
    rank: null,
  });
  const [shopItems, setShopItems] = useState<ShopItem[]>([]);
  const [adminGages, setAdminGages] = useState<Gage[]>([]);
  const [sprites, setSprites] = useState<Sprite[]>([]);
  const [fighters, setFighters] = useState<Fighter[]>([]);
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [tournaments, setTournaments] = useState<Tournament[]>([]);
  const [playableMatches, setPlayableMatches] = useState<PlayableMatch[]>([]);
  const [usingItem, setUsingItem] = useState<InventoryItem | null>(null);
  const [pendingUnregister, setPendingUnregister] = useState<Tournament | null>(null);
  const [pendingDeleteTournament, setPendingDeleteTournament] = useState<Tournament | null>(null);
  const [pendingCancelScore, setPendingCancelScore] = useState<{
    tournamentId: number;
    matchCode: string;
  } | null>(null);
  const [duels, setDuels] = useState<Duel[]>([]);
  // Action sur un duel en attente de confirmation (ConfirmModal)
  const [pendingDuelAction, setPendingDuelAction] = useState<{
    type: "cancel-result" | "cancel-duel";
    duel: Duel;
  } | null>(null);
  const actionBusyRef = useRef(false);

  const close = () => setModal(null);

  const withActionLock = useCallback(async <T,>(fn: () => Promise<T>): Promise<T | null> => {
    if (actionBusyRef.current) return null;
    actionBusyRef.current = true;
    try {
      return await fn();
    } finally {
      actionBusyRef.current = false;
    }
  }, []);

  const loadShopAndInventory = useCallback(async (loggedUser: User | null) => {
    try {
      const [gages, settings] = await Promise.all([
        apiJson<Gage[]>("/api/shop/gages"),
        apiJson<Settings>("/api/settings"),
      ]);
      const gageGain = settings?.duel_gage_win_reward ?? 50;

      if (gages) {
        setShopItems(
          gages.map((g) => ({
            id: g.id,
            name: g.name,
            gage: g.description,
            price: g.price,
            gain: g.reward ?? gageGain,
            image: g.image_url,
          }))
        );
      }

      if (loggedUser) {
        const rawInv = await apiJson<InventoryEntry[]>("/api/inventory?status=owned");
        if (rawInv) {
          const validEntries = rawInv.filter(
            (e): e is InventoryEntry & { gage: Gage } => e.gage !== null
          );
          const groupedByGageId = Map.groupBy(validEntries, (e) => e.gage.id);
          const invList = Array.from(groupedByGageId.values()).map((entries) => {
            const g = entries[0].gage;
            return {
              id: g.id,
              name: g.name,
              gage: g.description,
              price: g.price,
              gain: g.reward ?? gageGain,
              image: g.image_url,
              qty: entries.length,
              inventoryItemIds: entries.map((e) => e.id),
            };
          });
          setInventory(invList);
        }

        if (loggedUser.is_admin) {
          const [admGages, spList] = await Promise.all([
            apiJson<Gage[]>("/api/admin/gages"),
            apiJson<Sprite[]>("/api/shop/sprites"),
          ]);
          if (admGages) setAdminGages(admGages);
          if (spList) setSprites(spList);
        }
      }
    } catch (err) {
      console.error("Erreur chargement boutique/inventaire :", err);
    }
  }, []);

  const loadLeaderboard = useCallback(async () => {
    try {
      const data = await apiJson<LeaderboardEntry[]>("/api/users/leaderboard");
      if (data) setLeaderboard(data);
    } catch (err) {
      console.error("Erreur chargement classement :", err);
    }
  }, []);

  const loadStats = useCallback(async () => {
    try {
      const [meData, statsData, lbData] = await Promise.all([
        apiJson<User>("/api/auth/me"),
        apiJson<UserStats>("/api/users/me/stats"),
        apiJson<LeaderboardEntry[]>("/api/users/leaderboard"),
      ]);
      if (meData) {
        setUser(meData);
        setBalance(meData.balance);
      }
      if (statsData) {
        setStats(statsData);
      }
      if (lbData) {
        setLeaderboard(lbData);
      }
    } catch (err) {
      console.error("Erreur chargement stats :", err);
    }
  }, []);

  const loadTournamentsAndMatches = useCallback(async (loggedUser: User | null) => {
    try {
      // 1 seule requête HTTP au lieu de 1 + 2N requêtes (évite l'effet N+1 à 50 joueurs)
      const rawTournaments = await apiJson<RawTournament[]>("/api/tournaments?full=true");
      if (!rawTournaments) return;

      const detailed = rawTournaments.map((detail): Tournament => {
        const fallbackDate = formatShortDate(detail.created_at);
        const rulesList =
          Array.isArray(detail.rules) && detail.rules.length > 0
            ? detail.rules.map((r) =>
                typeof r === "string" ? r : r.value || `${r.label} : ${r.value}`
              )
            : ["1 contre 1", "Double Élimination", "3 vies · 7 min", "Objets : Off"];

        return {
          ...detail,
          date: detail.date_label || fallbackDate,
          max_players: detail.max_players || 32,
          rules: rulesList,
          matches: detail.matches || [],
        };
      });

      setTournaments(detailed);

      if (loggedUser) {
        const userMatches: PlayableMatch[] = [];
        for (const t of detailed) {
          const pMap = Object.fromEntries(
            (t.participants || []).map((p: Participant) => [
              p.user_id,
              p.display_name || p.username,
            ])
          );
          for (const m of t.matches || []) {
            if (
              m.status === "ready" &&
              m.betting_open !== false &&
              !m.started_at &&
              m.winner_id == null &&
              (m.player1_id === loggedUser.id || m.player2_id === loggedUser.id)
            ) {
              const oppId = m.player1_id === loggedUser.id ? m.player2_id : m.player1_id;
              const alreadyUsedByMe = (m.gages || []).some(
                (g) => g.imposer_id === loggedUser.id && g.status !== "cancelled"
              );
              userMatches.push({
                id: `t-${t.id}-${m.code}`,
                kind: "tournament",
                tournamentId: t.id,
                matchCode: m.code,
                targetId: oppId,
                opponent: oppId ? pMap[oppId] || `Joueur #${oppId}` : "Adversaire",
                info: alreadyUsedByMe
                  ? `${t.name} · Match ${m.code} (Objet déjà équipé)`
                  : `${t.name} · Match ${m.code}`,
                disabled: alreadyUsedByMe,
              });
            }
          }
        }

        // Pas d'objet sur les duels : seuls les matchs de tournoi sont proposés.
        setPlayableMatches(userMatches);
      }
    } catch (err) {
      console.error("Erreur chargement tournois :", err);
    }
  }, []);

  useEffect(() => {
    apiJson<Fighter[]>("/fighters/catalog.json")
      .then((data) => setFighters(Array.isArray(data) ? data : []))
      .catch(() => {});

    apiJson<User>("/api/auth/me")
      .then(async (data) => {
        if (data) {
          setUser(data);
          setBalance(data.balance);
          await Promise.all([
            loadStats(),
            loadShopAndInventory(data),
            loadTournamentsAndMatches(data),
          ]);
        } else {
          setUser(null);
        }
      })
      .catch(() => {
        setUser(null);
      })
      .finally(() => {
        setAuthChecked(true);
      });
  }, [loadShopAndInventory, loadStats, loadTournamentsAndMatches]);

  const loadDuels = useCallback(async () => {
    const data = await apiJson<Duel[]>("/api/duels").catch(() => null);
    if (data) setDuels(data);
  }, []);

  // Duels (et donc la notification du menu) rechargés au démarrage, toutes les 5s,
  // et dès qu'on revient sur l'onglet.
  const duelsUserId = user?.id;
  useEffect(() => {
    if (!duelsUserId) return;
    const refresh = () => {
      if (document.visibilityState === "visible" && !actionBusyRef.current) {
        loadDuels();
      }
    };
    const first = setTimeout(loadDuels, 0);
    const id = setInterval(refresh, 5000);
    document.addEventListener("visibilitychange", refresh);
    return () => {
      clearTimeout(first);
      clearInterval(id);
      document.removeEventListener("visibilitychange", refresh);
    };
  }, [duelsUserId, loadDuels]);

  // Synchronisation temps-réel légère (toutes les 5s) lorsque la modale Tournois est ouverte
  useEffect(() => {
    if (modal !== "signup" || !user) return;
    const id = setInterval(() => {
      if (document.visibilityState === "visible" && !actionBusyRef.current) {
        loadTournamentsAndMatches(user);
      }
    }, 5000);
    return () => clearInterval(id);
  }, [modal, user, loadTournamentsAndMatches]);

  // Rafraîchissement du solde de Tilts (toutes les 10s, onglet visible uniquement)
  const userId = user?.id;
  useEffect(() => {
    if (!userId) return;
    const refreshBalance = async () => {
      if (document.visibilityState !== "visible" || actionBusyRef.current) return;
      const me = await apiJson<User>("/api/auth/me").catch(() => null);
      if (me) setBalance(me.balance);
    };
    const id = setInterval(refreshBalance, 10000);
    document.addEventListener("visibilitychange", refreshBalance);
    return () => {
      clearInterval(id);
      document.removeEventListener("visibilitychange", refreshBalance);
    };
  }, [userId]);

  const handleLogin42 = async () => {
    try {
      const redirectUri = `${window.location.origin}/auth/callback`;
      const data = await apiJson<{ authorization_url: string }>(
        "/api/auth/oauth/42/authorize",
        {
          method: "POST",
          body: JSON.stringify({ redirect_uri: redirectUri }),
        }
      );
      if (data?.authorization_url) {
        window.location.href = data.authorization_url;
      }
    } catch (error) {
      console.error("Impossible de lancer la connexion 42 :", error);
    }
  };

  const handleBuy = (item: ShopItem) =>
    withActionLock(async () => {
      if (!user) return;
      const ok = await apiJson(`/api/shop/gages/${item.id}/purchase`, {
        method: "POST",
      });
      if (ok) {
        await Promise.all([loadStats(), loadShopAndInventory(user)]);
      }
    });

  const handleSaveGage = (gageId: number, payload: GagePayload) =>
    withActionLock(async () => {
      if (!user) return;
      const ok = await apiJson(`/api/admin/gages/${gageId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      if (ok) {
        await loadShopAndInventory(user);
      }
    });

  const handleCreateGage = (payload: GagePayload) =>
    withActionLock(async () => {
      if (!user) return null;
      const created = await apiJson("/api/admin/gages", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      if (created) {
        await loadShopAndInventory(user);
        return created;
      }
      return null;
    });

  const handleArchiveGage = (gageId: number) =>
    withActionLock(async () => {
      if (!user) return;
      const ok = await apiJson(`/api/admin/gages/${gageId}`, {
        method: "PATCH",
        body: JSON.stringify({ is_archived: true }),
      });
      if (ok) {
        await loadShopAndInventory(user);
      }
    });

  const handleEquip = (item: InventoryItem | null, match: PlayableMatch | null) =>
    withActionLock(async () => {
      if (!user || !item || !match || match.disabled) return;
      const inventoryItemId = item.inventoryItemIds?.[0];
      if (!inventoryItemId) return;

      const url =
        match.kind === "duel"
          ? `/api/duels/${match.duelId}/gages`
          : `/api/tournaments/${match.tournamentId}/matches/${match.matchCode}/gages`;

      const ok = await apiJson(url, {
        method: "POST",
        body: JSON.stringify({
          inventory_item_id: inventoryItemId,
          target_id: item.price === 0 ? user.id : match.targetId || user.id,
        }),
      });

      if (ok) {
        await Promise.all([
          loadShopAndInventory(user),
          loadTournamentsAndMatches(user),
        ]);
        close();
      }
    });

  const handlePublishTournament = (data: TournamentFormData) =>
    withActionLock(async () => {
      if (!user) return;
      const dateLabel = data.date
        ? `${formatShortDate(data.date + "T00:00")} · ${(data.time || "14:00").replace(":00", "h")}`
        : undefined;

      const startsAt = data.date
        ? `${data.date}T${data.time || "14:00"}:00`
        : undefined;

      const created = await apiJson("/api/tournaments", {
        method: "POST",
        body: JSON.stringify({
          name: data.name,
          rewards: { champion: Math.min(Math.max(Number(data.reward) || 200, 0), 100000) },
          scheduled_date: data.date || undefined,
          starts_at: startsAt,
          date_label: dateLabel,
          max_players: Number(data.maxPlayers) || 16,
          has_losers_bracket: data.losers_bracket !== "Non",
          rules: [
            { label: "Format", value: String(data.format) },
            { label: "Vies", value: `${data.lives} vies` },
            { label: "Temps", value: String(data.time_limit) },
            { label: "Objets", value: `Objets : ${data.items}` },
          ],
        }),
      });

      if (created) {
        await loadTournamentsAndMatches(user);
        setModal("signup");
      }
    });

  const handleSignupTournament = (t: Tournament | null) =>
    withActionLock(async () => {
      if (!user || !t) return;
      const ok = await apiJson(`/api/tournaments/${t.id}/register`, {
        method: "POST",
      });
      if (ok) {
        await Promise.all([loadTournamentsAndMatches(user), loadStats()]);
      }
    });

  const handleUnregisterTournament = (t: Tournament | null) =>
    withActionLock(async () => {
      if (!user || !t) return;
      const ok = await apiJson(`/api/tournaments/${t.id}/register`, {
        method: "DELETE",
      });
      if (ok) {
        setPendingUnregister(null);
        await Promise.all([loadTournamentsAndMatches(user), loadStats()]);
        setModal("signup");
      }
    });

  const handleDeleteTournament = (t: Tournament | null) =>
    withActionLock(async () => {
      if (!user?.is_admin || !t) return;
      const ok = await apiJson(`/api/tournaments/${t.id}`, {
        method: "DELETE",
      });
      if (ok) {
        setPendingDeleteTournament(null);
        await Promise.all([
          loadTournamentsAndMatches(user),
          loadShopAndInventory(user),
          loadStats(),
        ]);
        setModal("signup");
      }
    });

  const handleGenerateBracket = (t: Tournament | null) =>
    withActionLock(async () => {
      if (!user || !t) return;
      const ok = await apiJson(`/api/tournaments/${t.id}/generate`, {
        method: "POST",
      });
      if (ok) {
        await Promise.all([loadTournamentsAndMatches(user), loadStats()]);
      }
    });

  const handleAddBot = (t: Tournament | null) =>
    withActionLock(async () => {
      if (!user || !t) return;
      const ok = await apiJson(`/api/tournaments/${t.id}/bots`, {
        method: "POST",
      });
      if (ok) {
        await loadTournamentsAndMatches(user);
      }
    });

  const handleReportScore = (
    tournamentId: number,
    matchCode: string,
    score1: number,
    score2: number
  ) =>
    withActionLock(async () => {
      if (!user) return;
      const ok = await apiJson(
        `/api/tournaments/${tournamentId}/matches/${matchCode}/score`,
        {
          method: "PUT",
          body: JSON.stringify({ score1, score2 }),
        }
      );
      if (ok) {
        await Promise.all([loadTournamentsAndMatches(user), loadStats()]);
      }
    });

  // lock = true : lance le match (ferme les paris) ; false : annule le lancement (rouvre les paris)
  const handleStartMatch = (tournamentId: number, matchCode: string, lock = true) =>
    withActionLock(async () => {
      if (!user?.is_admin) return;
      const ok = await apiJson(`/api/tournaments/${tournamentId}/matches/${matchCode}/start`, {
        method: lock ? "POST" : "DELETE",
      });
      if (ok) {
        await loadTournamentsAndMatches(user);
      }
    });

  const handlePlaceBet = async (
    tournamentId: number,
    matchCode: string,
    pickedPlayerId: number,
    amount: number
  ): Promise<{ ok: boolean; error?: string }> => {
    if (!user) return { ok: false, error: "Connecte-toi pour parier" };
    const result = await withActionLock(async () => {
      const res = await fetch(`/api/tournaments/${tournamentId}/matches/${matchCode}/bets`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ picked_player_id: pickedPlayerId, amount }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => null);
        const detail = typeof data?.detail === "string" ? data.detail : "Pari refusé";
        return { ok: false, error: detail };
      }
      await loadStats();
      return { ok: true };
    });
    return result ?? { ok: false, error: "Action déjà en cours" };
  };

  // Supprime la session côté serveur (base + cookie) puis recharge la page :
  // tout l'état est remis à zéro.
  const handleLogout = async () => {
    await fetch("/api/auth/logout", { method: "POST" }).catch(() => null);
    window.location.href = "/";
  };

  // --- Duels ---

  // Appel API qui renvoie le message d'erreur du backend (pour l'afficher)
  const apiAction = async (
    url: string,
    method: string,
    body?: unknown
  ): Promise<{ ok: boolean; error?: string }> => {
    const res = await fetch(url, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (res.ok) return { ok: true };
    const data = await res.json().catch(() => null);
    return { ok: false, error: typeof data?.detail === "string" ? data.detail : "Action refusée" };
  };

  const duelAction = async (url: string, method: string, body?: unknown, refreshStats = false) => {
    const result = await withActionLock(async () => {
      const res = await apiAction(url, method, body);
      if (res.ok) await Promise.all([loadDuels(), refreshStats ? loadStats() : null]);
      return res;
    });
    return result ?? { ok: false, error: "Action déjà en cours" };
  };

  const handleChallenge = (opponentId: number) =>
    duelAction("/api/duels", "POST", { opponent_id: opponentId });

  const handleRespondDuel = (duelId: number, accept: boolean) =>
    duelAction(`/api/duels/${duelId}/${accept ? "accept" : "refuse"}`, "POST");

  const handleValidateDuel = (duelId: number) =>
    duelAction(`/api/admin/duels/${duelId}/validate`, "POST");

  // lock = true : lance le duel (ferme les paris) ; false : dé-lock (rouvre les paris)
  const handleLockDuel = (duelId: number, lock: boolean) =>
    duelAction(`/api/admin/duels/${duelId}/start`, lock ? "POST" : "DELETE");

  const handleReportDuelResult = (duelId: number, challengerScore: number, opponentScore: number) =>
    duelAction(
      `/api/admin/duels/${duelId}/result`,
      "PUT",
      { challenger_score: challengerScore, opponent_score: opponentScore },
      true
    );

  const handlePlaceDuelBet = (duelId: number, pickedPlayerId: number, amount: number) =>
    duelAction(
      `/api/duels/${duelId}/bets`,
      "POST",
      { picked_player_id: pickedPlayerId, amount },
      true
    );

  const handleConfirmDuelAction = async () => {
    const action = pendingDuelAction;
    setPendingDuelAction(null);
    if (action?.type === "cancel-result") {
      await duelAction(`/api/admin/duels/${action.duel.id}/result`, "DELETE", undefined, true);
    } else if (action?.type === "cancel-duel") {
      await duelAction(`/api/duels/${action.duel.id}/cancel`, "POST", undefined, true);
    }
    setModal("duels");
  };

  const duelPlayers = (d?: Duel) =>
    d
      ? `${d.challenger.display_name || d.challenger.username} vs ${
          d.opponent.display_name || d.opponent.username
        }`
      : "";

  // Duels qui attendent une action de ma part (réponse, ou confirmation si admin)
  const duelsToHandle = duels.filter(
    (d) =>
      (d.status === "pending" && d.opponent.id === user?.id) ||
      (d.status === "accepted" && user?.is_admin)
  ).length;

  const handleCancelScore = (pending: { tournamentId: number; matchCode: string } | null) =>
    withActionLock(async () => {
      if (!user?.is_admin || !pending) return;
      const ok = await apiJson(
        `/api/tournaments/${pending.tournamentId}/matches/${pending.matchCode}/score`,
        { method: "DELETE" }
      );
      setPendingCancelScore(null);
      if (ok) {
        await Promise.all([loadTournamentsAndMatches(user), loadStats()]);
      }
      setModal("signup");
    });

  const handleValidateGage = (useId: number, completed: boolean) =>
    withActionLock(async () => {
      if (!user?.is_admin) return;
      const ok = await apiJson(`/api/admin/gage-uses/${useId}/validation`, {
        method: "PUT",
        body: JSON.stringify({ completed }),
      });
      if (ok) {
        await Promise.all([loadTournamentsAndMatches(user), loadStats()]);
      }
    });

  const handleAdjustTilt = (targetUserId: number, amount: number, reason: string) =>
    withActionLock(async () => {
      if (!user?.is_admin) return;
      const ok = await apiJson(`/api/admin/users/${targetUserId}/tilt`, {
        method: "POST",
        body: JSON.stringify({ amount, reason }),
      });
      if (ok) {
        await loadStats();
      }
    });

  const handleBulkAdjustTilt = (targetUserIds: number[], amount: number, reason: string) =>
    withActionLock(async () => {
      if (!user?.is_admin || !targetUserIds?.length) return;
      const ok = await apiJson("/api/admin/users/tilt-bulk", {
        method: "POST",
        body: JSON.stringify({ user_ids: targetUserIds, amount, reason }),
      });
      if (ok) {
        await loadStats();
      }
    });

  const fighterColorByImage = useMemo(
    () => new Map(fighters.map((f) => [f.image, f.color])),
    [fighters]
  );

  return (
    <SmashIntro mp4Src="/smash-video.mp4">
      {authChecked && !user && (
        <div className="smash-intro__actions">
          <MeleeButton text="Connexion" onClick={handleLogin42} />
        </div>
      )}

      {authChecked && user && (
        <div className="smash-intro__tilts">
          <span className="smash-intro__tilts-val">{fmt(balance)}</span>
          <span className="smash-intro__tilts-label">Tilts</span>
          <img
            src="/mario-coin.svg"
            alt="Pièce Mario"
            className="smash-intro__tilts-coin"
            draggable={false}
          />
        </div>
      )}

      {authChecked && user?.is_admin && (
        <div className="smash-intro__actions">
          <MeleeButton
            text="Setting Admin"
            onClick={() => {
              loadTournamentsAndMatches(user);
              setModal("create");
            }}
          />
        </div>
      )}

      {authChecked && user && (
        <div className="smash-intro__menu">
          <div className="smash-intro__menu-row">
            {/* Colonne à gauche du logo : même sens que ceux de droite */}
            <div className="smash-intro__menu-col smash-intro__menu-col--left">
              <MeleeButton
                text="Profil"
                onClick={() => {
                  loadStats();
                  setModal("profile");
                }}
              />
              <MeleeButton
                text="Tournois"
                onClick={() => {
                  loadTournamentsAndMatches(user);
                  setModal("signup");
                }}
              />
              <MeleeButton
                text={duelsToHandle ? `Duels (${duelsToHandle})` : "Duels"}
                onClick={() => {
                  loadDuels();
                  setModal("duels");
                }}
              />
            </div>

            {/* Colonne à droite du logo : pointes vers le centre */}
            <div className="smash-intro__menu-col smash-intro__menu-col--right">
              <MeleeButton
                text="Stats"
                onClick={() => {
                  loadLeaderboard();
                  setModal("stats");
                }}
              />
              <MeleeButton
                text="Shop"
                onClick={() => {
                  loadShopAndInventory(user);
                  setModal("shop");
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Modales Melee */}
      <ShopModal
        open={modal === "shop"}
        items={shopItems}
        balance={balance}
        isAdmin={!!user?.is_admin}
        onAdminShop={() => {
          loadShopAndInventory(user);
          setModal("shop-admin");
        }}
        onBuy={handleBuy}
        onClose={close}
      />

      <ShopAdminModal
        open={modal === "shop-admin"}
        gages={adminGages}
        sprites={sprites}
        onSaveGage={handleSaveGage}
        onCreateGage={handleCreateGage}
        onArchiveGage={handleArchiveGage}
        onOpenTournamentCreate={() => setModal("create")}
        onOpenAdminUsers={() => {
          loadLeaderboard();
          loadTournamentsAndMatches(user);
          setModal("admin-users");
        }}
        onClose={close}
      />

      <InventoryModal
        open={modal === "inv"}
        items={inventory}
        onUse={(it: InventoryItem) => {
          setUsingItem(it);
          loadTournamentsAndMatches(user);
          setModal("use");
        }}
        onClose={() => setModal("profile")}
      />

      <UseItemModal
        open={modal === "use"}
        item={usingItem}
        matches={playableMatches}
        onConfirm={handleEquip}
        onBack={() => setModal("inv")}
        onClose={close}
      />

      <TournamentSignupModal
        open={modal === "signup"}
        tournaments={tournaments}
        shopItems={shopItems}
        currentUserId={user?.id}
        isAdmin={!!user?.is_admin}
        onSignup={handleSignupTournament}
        onUnregister={(t: Tournament) => {
          setPendingUnregister(t);
          setModal("confirm");
        }}
        onAddBot={handleAddBot}
        onGenerateBracket={handleGenerateBracket}
        onReportScore={handleReportScore}
        onCancelScore={(tournamentId: number, matchCode: string) => {
          setPendingCancelScore({ tournamentId, matchCode });
          setModal("confirm-cancel-score");
        }}
        onPlaceBet={handlePlaceBet}
        onStartMatch={handleStartMatch}
        balance={balance}
        onValidateGage={handleValidateGage}
        onDeleteTournament={(t: Tournament) => {
          setPendingDeleteTournament(t);
          setModal("confirm-delete-tournament");
        }}
        onOpenCreate={() => setModal("create")}
        onOpenShopAdmin={() => {
          loadShopAndInventory(user);
          setModal("shop-admin");
        }}
        onOpenAdminUsers={() => {
          loadLeaderboard();
          loadTournamentsAndMatches(user);
          setModal("admin-users");
        }}
        onClose={close}
      />

      <TournamentCreateModal
        open={modal === "create"}
        tournaments={tournaments}
        onClose={close}
        onDeleteTournament={(t: Tournament) => {
          setPendingDeleteTournament(t);
          setModal("confirm-delete-tournament");
        }}
        onOpenTournamentSignup={() => {
          loadTournamentsAndMatches(user);
          setModal("signup");
        }}
        onOpenShopAdmin={() => {
          loadShopAndInventory(user);
          setModal("shop-admin");
        }}
        onOpenAdminUsers={() => {
          loadLeaderboard();
          loadTournamentsAndMatches(user);
          setModal("admin-users");
        }}
        onPublish={handlePublishTournament}
      />

      <LeaderboardModal
        open={modal === "stats"}
        players={leaderboard}
        currentUserId={user?.id}
        isAdmin={!!user?.is_admin}
        onOpenAdminUsers={() => {
          loadLeaderboard();
          loadTournamentsAndMatches(user);
          setModal("admin-users");
        }}
        onClose={close}
      />

      <AdminUsersModal
        open={modal === "admin-users"}
        players={leaderboard}
        tournaments={tournaments}
        onAdjustTilt={handleAdjustTilt}
        onBulkAdjustTilt={handleBulkAdjustTilt}
        onOpenTournamentCreate={() => setModal("create")}
        onOpenShopAdmin={() => {
          loadShopAndInventory(user);
          setModal("shop-admin");
        }}
        onClose={close}
      />

      <ConfirmModal
        open={modal === "confirm"}
        question="Quitter le tournoi ?"
        caption="Tu pourras te réinscrire tant que l'arbre n'est pas lancé"
        onYes={() => handleUnregisterTournament(pendingUnregister)}
        onNo={() => setModal("signup")}
      />

      <ConfirmModal
        open={modal === "confirm-delete-tournament"}
        question={`Supprimer ${pendingDeleteTournament?.name || "ce tournoi"} ?`}
        caption="Action irréversible : le tournoi et son arbre seront supprimés"
        onYes={() => handleDeleteTournament(pendingDeleteTournament)}
        onNo={() => setModal("signup")}
      />

      <ConfirmModal
        open={modal === "confirm-cancel-score"}
        question={`Dévalider le match ${pendingCancelScore?.matchCode ?? ""} ?`}
        caption="Les gains déjà versés sont repris, les paris attendent le nouveau résultat. Les résultats des matchs suivants qui en dépendent sont aussi annulés."
        onYes={() => handleCancelScore(pendingCancelScore)}
        onNo={() => {
          setPendingCancelScore(null);
          setModal("signup");
        }}
      />

      <DuelsModal
        open={modal === "duels"}
        onClose={close}
        duels={duels}
        currentUserId={user?.id}
        isAdmin={!!user?.is_admin}
        balance={balance}
        onChallenge={handleChallenge}
        onRespond={handleRespondDuel}
        onValidateDuel={handleValidateDuel}
        onLockDuel={handleLockDuel}
        onReportResult={handleReportDuelResult}
        onPlaceBet={handlePlaceDuelBet}
        onCancelResult={(duel: Duel) => {
          setPendingDuelAction({ type: "cancel-result", duel });
          setModal("confirm-duel-action");
        }}
        onCancelDuel={(duel: Duel) => {
          setPendingDuelAction({ type: "cancel-duel", duel });
          setModal("confirm-duel-action");
        }}
      />

      <ConfirmModal
        open={modal === "confirm-logout"}
        question="Se déconnecter ?"
        caption="Tu pourras te reconnecter avec ton compte 42"
        onYes={handleLogout}
        onNo={() => setModal("profile")}
      />

      <ConfirmModal
        open={modal === "confirm-duel-action"}
        question={
          pendingDuelAction?.type === "cancel-result"
            ? `Dévalider le duel ${duelPlayers(pendingDuelAction?.duel)} ?`
            : `Annuler le duel ${duelPlayers(pendingDuelAction?.duel)} ?`
        }
        caption={
          pendingDuelAction?.type === "cancel-result"
            ? "Les gains déjà versés sont repris, les paris attendent le nouveau résultat."
            : "Le duel est définitivement annulé et tous les paris sont remboursés."
        }
        onYes={handleConfirmDuelAction}
        onNo={() => {
          setPendingDuelAction(null);
          setModal("duels");
        }}
      />

      <ProfileModal
        open={modal === "profile"}
        onClose={close}
        onAvatarClick={() => setModal("char-select")}
        onOpenInventory={() => {
          loadShopAndInventory(user);
          setModal("inv");
        }}
        onLogout={() => setModal("confirm-logout")}
        player={{
          login: user?.username ?? "player",
          campus: user?.display_name ?? "42",
          avatar:
            stats.avatar_url ||
            user?.avatar_url ||
            (user?.username ? `https://cdn.intra.42.fr/users/${user.username}.jpg` : undefined),
          avatarColor: fighterColorByImage.get(stats.avatar_url || user?.avatar_url || ""),
          wins: stats.wins,
          losses: stats.losses,
          tournaments: stats.tournaments,
          rank: stats.rank,
          balance,
        }}
      />

      <CharacterSelectScreen
        open={modal === "char-select"}
        characters={fighters}
        selectedId={stats.avatar_url || user?.avatar_url}
        login={user?.username ?? "player"}
        assetsPath="/smash"
        onSelect={async (char: Fighter | null) => {
          if (char?.image) {
            const res = await fetch("/api/users/me/avatar", {
              method: "PATCH",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ avatar_url: char.image }),
            });
            if (res.ok) {
              await Promise.all([loadStats(), loadTournamentsAndMatches(user)]);
            }
          }
          setModal("profile");
        }}
        onClose={() => setModal("profile")}
      />
    </SmashIntro>
  );
}
