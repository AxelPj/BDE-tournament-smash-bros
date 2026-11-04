"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import SmashIntro from "./componant/ui/SmashIntro";
import MeleeButton from "./componant/ui/MeleeButton";
import ShopModal from "./componant/modals/ShopModal";
import InventoryModal from "./componant/modals/InventoryModal";
import UseItemModal from "./componant/modals/UseItemModal";
import TournamentSignupModal from "./componant/modals/TournamentSignupModal";
import TournamentCreateModal from "./componant/modals/TournamentCreateModal";
import ConfirmModal from "./componant/modals/ConfirmModal";
import ProfileModal from "./componant/modals/ProfileModal";
import ShopAdminModal from "./componant/modals/ShopAdminModal";
import CharacterSelectScreen from "./componant/modals/CharacterSelectScreen";
import LeaderboardModal from "./componant/modals/LeaderboardModal";
import AdminUsersModal from "./componant/modals/AdminUsersModal";
import { apiJson, fmt, formatShortDate } from "./lib/utils";

interface User {
  id: number;
  username: string;
  display_name: string;
  avatar_url?: string | null;
  is_admin: boolean;
  intra_id: number | null;
  balance: number;
}

interface UserStats {
  wins: number;
  losses: number;
  tournaments: number;
  rank: number | null;
  avatar_url?: string | null;
}

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
  const [shopItems, setShopItems] = useState<any[]>([]);
  const [adminGages, setAdminGages] = useState<any[]>([]);
  const [sprites, setSprites] = useState<any[]>([]);
  const [fighters, setFighters] = useState<any[]>([]);
  const [inventory, setInventory] = useState<any[]>([]);
  const [leaderboard, setLeaderboard] = useState<any[]>([]);
  const [tournaments, setTournaments] = useState<any[]>([]);
  const [playableMatches, setPlayableMatches] = useState<any[]>([]);
  const [usingItem, setUsingItem] = useState<any | null>(null);
  const [pendingUnregister, setPendingUnregister] = useState<any | null>(null);
  const [pendingDeleteTournament, setPendingDeleteTournament] = useState<any | null>(null);
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
        apiJson<any[]>("/api/shop/gages"),
        apiJson<any>("/api/settings"),
      ]);
      const gageGain = settings?.duel_gage_win_reward ?? 50;

      if (gages) {
        setShopItems(
          gages.map((g: any) => ({
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
        const rawInv = await apiJson<any[]>("/api/inventory?status=owned");
        if (rawInv) {
          const validEntries = rawInv.filter((e) => e.gage);
          const groupedByGageId = Map.groupBy(validEntries, (e) => e.gage.id as number);
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
            apiJson<any[]>("/api/admin/gages"),
            apiJson<any[]>("/api/shop/sprites"),
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
      const data = await apiJson<any[]>("/api/users/leaderboard");
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
        apiJson<any[]>("/api/users/leaderboard"),
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
      const [rawTournaments, duels] = await Promise.all([
        apiJson<any[]>("/api/tournaments?full=true"),
        loggedUser ? apiJson<any[]>("/api/duels/mine") : Promise.resolve(null),
      ]);
      if (!rawTournaments) return;

      const detailed = rawTournaments.map((detail: any) => {
        const fallbackDate = formatShortDate(detail.created_at);
        const rulesList =
          Array.isArray(detail.rules) && detail.rules.length > 0
            ? detail.rules.map((r: any) =>
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
        const userMatches: any[] = [];
        for (const t of detailed) {
          const pMap = Object.fromEntries(
            (t.participants || []).map((p: any) => [
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
                (g: any) => g.imposer_id === loggedUser.id && g.status !== "cancelled"
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

        if (duels) {
          for (const d of duels) {
            if (d.status === "validated") {
              const opp = d.challenger.id === loggedUser.id ? d.opponent : d.challenger;
              userMatches.push({
                id: `d-${d.id}`,
                kind: "duel",
                duelId: d.id,
                targetId: opp.id,
                opponent: opp.display_name || opp.username,
                info: `Duel · Mise ${d.stake} Tilt`,
              });
            }
          }
        }

        setPlayableMatches(userMatches);
      }
    } catch (err) {
      console.error("Erreur chargement tournois :", err);
    }
  }, []);

  useEffect(() => {
    apiJson<any[]>("/fighters/catalog.json")
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

  const handleBuy = (item: any) =>
    withActionLock(async () => {
      if (!user) return;
      const ok = await apiJson(`/api/shop/gages/${item.id}/purchase`, {
        method: "POST",
      });
      if (ok) {
        await Promise.all([loadStats(), loadShopAndInventory(user)]);
      }
    });

  const handleSaveGage = (gageId: number, payload: any) =>
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

  const handleCreateGage = (payload: any) =>
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

  const handleEquip = (item: any, match: any) =>
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

  const handlePublishTournament = (data: any) =>
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

  const handleSignupTournament = (t: any) =>
    withActionLock(async () => {
      if (!user || !t) return;
      const ok = await apiJson(`/api/tournaments/${t.id}/register`, {
        method: "POST",
      });
      if (ok) {
        await Promise.all([loadTournamentsAndMatches(user), loadStats()]);
      }
    });

  const handleUnregisterTournament = (t: any) =>
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

  const handleDeleteTournament = (t: any) =>
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

  const handleGenerateBracket = (t: any) =>
    withActionLock(async () => {
      if (!user || !t) return;
      const ok = await apiJson(`/api/tournaments/${t.id}/generate`, {
        method: "POST",
      });
      if (ok) {
        await Promise.all([loadTournamentsAndMatches(user), loadStats()]);
      }
    });

  const handleAddBot = (t: any) =>
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
        onUse={(it: any) => {
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
        onUnregister={(t: any) => {
          setPendingUnregister(t);
          setModal("confirm");
        }}
        onAddBot={handleAddBot}
        onGenerateBracket={handleGenerateBracket}
        onReportScore={handleReportScore}
        onValidateGage={handleValidateGage}
        onDeleteTournament={(t: any) => {
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
        onDeleteTournament={(t: any) => {
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

      <ProfileModal
        open={modal === "profile"}
        onClose={close}
        onAvatarClick={() => setModal("char-select")}
        onOpenInventory={() => {
          loadShopAndInventory(user);
          setModal("inv");
        }}
        player={{
          login: user?.username ?? "player",
          campus: user?.display_name ?? "42",
          avatar:
            stats.avatar_url ||
            user?.avatar_url ||
            (user?.username ? `https://cdn.intra.42.fr/users/${user.username}.jpg` : undefined),
          avatarColor: fighterColorByImage.get(stats.avatar_url || user?.avatar_url),
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
        onSelect={async (char: any) => {
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
