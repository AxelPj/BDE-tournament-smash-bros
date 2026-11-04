import { useEffect, useMemo, useRef, useState } from "react";
import MeleeFrame, { Panel, PanelRow, Sep } from "../ui/MeleeFrame";
import MeleeButton from "../ui/MeleeButton";
import { apiJson, fmt } from "../../lib/utils";

const SMASH_ITEM_IMAGES = {
  "trophee aide": "/items/item_img01.png",
  "poke ball": "/items/item_img02.png",
  pokeball: "/items/item_img02.png",
  "master ball": "/items/item_img03.png",
  "fer letal": "/items/item_img04.png",
  baton: "/items/item_img05.png",
  bombinet: "/items/item_img06.png",
  "fausse balle smash": "/items/item_img07.png",
  pistobanane: "/items/item_img08.png",
  "champinocif ambulant": "/items/item_img09.png",
  "super anneau etoile": "/items/item_img10.png",
  "trou noir": "/items/item_img11.png",
  "flingue rageur": "/items/item_img12.png",
  "faux de la mort": "/items/item_img13.png",
  "champ de soin": "/items/item_img14.png",
  "pousse apaisante": "/items/item_img15.png",
  "balle diabolique": "/items/item_img16.png",
  "morceaux de dragoon": "/items/item_list01.png",
  "maxi-tomate": "/items/item_list02.png",
  "super champi": "/items/item_list03.png",
  champignon: "/items/item_list03.png",
  "masque de lapin": "/items/item_list04.png",
  chronometre: "/items/item_list05.png",
  "epee laser": "/items/item_list06.png",
  "baton etoile": "/items/item_list07.png",
  marteau: "/items/item_list08.png",
  "nintendo scope": "/items/item_list09.png",
  pistolaser: "/items/item_list10.png",
  "bob-omb": "/items/item_list11.png",
  "bombe x": "/items/item_list12.png",
  "bombe hocotate": "/items/item_list13.png",
  "tete brulee": "/items/item_list14.png",
  "mr. saturn": "/items/item_list15.png",
  bumper: "/items/item_list16.png",
  "carapace a epines": "/items/item_list17.png",
  scarabee: "/items/item_list18.png",
  cocotte: "/items/item_list19.png",
  ruche: "/items/item_list20.png",
  foreuse: "/items/item_list21.png",
  "boss galaga": "/items/item_list22.png",
  "badge franklin": "/items/item_list23.png",
  "attaque en vrille": "/items/item_list24.png",
  "super feuille": "/items/item_list25.png",
  caisse: "/items/item_list26.png",
  tonneau: "/items/item_list27.png",
  capsule: "/items/item_list28.png",
  "balle smash": "/items/item_list29.png",
  "morceaux de la genese": "/items/item_list30.png",
  "caisse explosive": "/items/item_list31.png",
  "sac de sable": "/items/item_list32.png",
  nourriture: "/items/item_list33.png",
  "receptacle de coeur": "/items/item_list34.png",
  "fee en bouteille": "/items/item_list35.png",
  "champi poison": "/items/item_list36.png",
  "super etoile": "/items/item_list37.png",
  etoile: "/items/item_list37.png",
  "etoile warp": "/items/item_list38.png",
  "caisse de metal": "/items/item_list39.png",
  "curry extrafort": "/items/item_list40.png",
  eclair: "/items/item_list41.png",
  "bill balle": "/items/item_list42.png",
  "batte de base-ball": "/items/item_list43.png",
  "marteau en or": "/items/item_list44.png",
  "marteau dore": "/items/item_list44.png",
  "sceptre de lip": "/items/item_list45.png",
  "barre de feu": "/items/item_list46.png",
  "massue minerai": "/items/item_list47.png",
  "fleur de feu": "/items/item_list48.png",
  "jarre magique": "/items/item_list49.png",
  "steel diver": "/items/item_list50.png",
  "bombe a detection": "/items/item_list51.png",
  "carapace verte": "/items/item_list52.png",
  congelo: "/items/item_list53.png",
  "bombe gluante": "/items/item_list54.png",
  "bombe intelligente": "/items/item_list55.png",
  "noix mojo": "/items/item_list56.png",
  "boule fumee": "/items/item_list57.png",
  piege: "/items/item_list58.png",
  "peau de banane": "/items/item_list59.png",
  unira: "/items/item_list60.png",
  "ballon de foot": "/items/item_list61.png",
  "missile teigneux": "/items/item_list62.png",
  "bloc pow": "/items/item_list63.png",
  boomerang: "/items/item_list64.png",
  "oeil-qui-tue": "/items/item_list65.png",
  "bouclier dorsal": "/items/item_list66.png",
  "ceinture-fusee": "/items/item_list67.png",
  "drapeau special": "/items/item_list68.png",
  "caisse roulante": "/items/item_list69.png",
  "ballon surprise": "/items/item_list70.png",
  herbe: "/items/item_list71.png",
};

function normalizeItemName(name) {
  return String(name || "")
    .toLowerCase()
    .replace(/œ/g, "oe")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim();
}

function resolveGageImg(g, shopItems = []) {
  if (g?.image_url) return g.image_url;
  const key = normalizeItemName(g?.name);
  if (!key) return "/items/item_list29.png";
  const fromShop = shopItems.find((it) => normalizeItemName(it.name) === key);
  if (fromShop?.image) return fromShop.image;
  if (SMASH_ITEM_IMAGES[key]) return SMASH_ITEM_IMAGES[key];
  for (const [k, url] of Object.entries(SMASH_ITEM_IMAGES)) {
    if (key.includes(k) || k.includes(key)) return url;
  }
  return "/items/item_list29.png";
}

function PlayerAvatar({ player }) {
  const [imgErr, setImgErr] = useState(false);
  if (!player) {
    return <span className="mm-bavatar">?</span>;
  }
  const src =
    !imgErr &&
    (player.avatar_url ||
      (player.username ? `https://cdn.intra.42.fr/users/${player.username}.jpg` : null));
  const initial = (player.display_name || player.username || "?").charAt(0).toUpperCase();

  return (
    <span className="mm-bavatar">
      {src ? (
        <img src={src} alt={player.display_name || player.username} onError={() => setImgErr(true)} />
      ) : (
        initial
      )}
    </span>
  );
}

/**
 * Bouton « Parier » + formulaire de pari sur un match de tournoi.
 * Affiche les cotes actuelles (pari mutuel) récupérées depuis l'API.
 */
function BetBox({ tournamentId, match, getPlayerName, balance, market, onPlaceBet, onBetPlaced }) {
  const [openForm, setOpenForm] = useState(false);
  const [pick, setPick] = useState(null);
  const [amount, setAmount] = useState(10);
  const [msg, setMsg] = useState(null); // { ok: bool, text: string }

  const players = [match.player1_id, match.player2_id];
  const oddsOf = (uid) => market?.players?.find((p) => p.user_id === uid);

  if (!openForm) {
    return (
      <MeleeButton
        text="Parier"
        height={38}
        onClick={() => {
          setOpenForm(true);
          setMsg(null);
        }}
      />
    );
  }

  const validAmount = Number.isInteger(amount) && amount >= 1 && amount <= (balance ?? 0);

  const submit = async () => {
    if (!pick || !validAmount) return;
    const res = await onPlaceBet?.(tournamentId, match.code, pick, amount);
    if (res?.ok) {
      setMsg({ ok: true, text: `Pari de ${amount} Tilts sur ${getPlayerName(pick)} enregistré !` });
      setPick(null);
      onBetPlaced?.();
    } else {
      setMsg({ ok: false, text: res?.error || "Pari refusé" });
    }
  };

  const choiceStyle = (selected) => ({
    flex: 1,
    cursor: "pointer",
    fontSize: "clamp(11px, 1.05cqw, 16px)",
    padding: ".35cqw .5cqw",
    textAlign: "center",
    borderColor: selected ? "#ffd000" : "#3a42e6",
    background: selected ? "rgba(255, 208, 0, .25)" : "rgba(20, 24, 80, .6)",
    color: "#fff",
    display: "flex",
    flexDirection: "column",
    gap: ".15cqw",
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: ".5cqw" }}>
      <span className="mm-ptag" style={{ color: "#ffd000" }}>
        Parier · {market ? fmt(market.total_bettors) : "…"} parieur
        {market?.total_bettors > 1 ? "s" : ""}
      </span>
      <div style={{ display: "flex", gap: ".4cqw" }}>
        {players.map((uid) => {
          const o = oddsOf(uid);
          return (
            <button
              key={uid}
              type="button"
              className="mm-field"
              style={choiceStyle(pick === uid)}
              onClick={() => setPick(uid)}
            >
              <span style={{ fontWeight: 900, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {getPlayerName(uid)}
              </span>
              <span style={{ fontSize: "clamp(10px, .9cqw, 14px)", opacity: 0.85 }}>
                {o?.odds
                  ? `Cote x${o.odds} · ${o.bettors} parieur${o.bettors > 1 ? "s" : ""}`
                  : "Aucun parieur"}
              </span>
            </button>
          );
        })}
      </div>
      <div className="mm-prow" style={{ alignItems: "center" }}>
        <span style={{ fontSize: "clamp(12px, 1.15cqw, 18px)" }}>
          Mise (solde {fmt(balance)})
        </span>
        <input
          type="number"
          min={1}
          max={balance ?? 0}
          className="mm-field"
          style={{
            width: "clamp(64px, 5.5cqw, 90px)",
            padding: "clamp(4px, .35cqw, 8px) clamp(6px, .5cqw, 10px)",
            fontSize: "clamp(13px, 1.25cqw, 20px)",
          }}
          value={amount}
          onChange={(e) => setAmount(Math.floor(Number(e.target.value)))}
        />
      </div>
      {msg && (
        <span
          style={{
            fontSize: "clamp(11px, 1cqw, 15px)",
            fontWeight: 800,
            color: msg.ok ? "#4ade80" : "#f87171",
          }}
        >
          {msg.text}
        </span>
      )}
      <div style={{ display: "flex", gap: ".4cqw" }}>
        <MeleeButton
          text="Confirmer"
          selected={Boolean(pick) && validAmount}
          disabled={!pick || !validAmount}
          height={34}
          onClick={submit}
        />
        <MeleeButton text="Annuler" height={34} onClick={() => setOpenForm(false)} />
      </div>
    </div>
  );
}

function formatCountdown(startsAtIso, nowMs) {
  if (!startsAtIso || !nowMs) return null;
  const target = new Date(startsAtIso).getTime();
  if (Number.isNaN(target)) return null;
  const diff = Math.max(0, Math.floor((target - nowMs) / 1000));
  if (diff <= 0) return { expired: true, text: "00h 00m 00s · Lancement !" };

  const days = Math.floor(diff / 86400);
  const hours = Math.floor((diff % 86400) / 3600);
  const mins = Math.floor((diff % 3600) / 60);
  const secs = diff % 60;
  const pad = (n) => String(n).padStart(2, "0");

  const text =
    days > 0
      ? `${days}j ${pad(hours)}h ${pad(mins)}m ${pad(secs)}s`
      : `${pad(hours)}h ${pad(mins)}m ${pad(secs)}s`;
  return { expired: false, text };
}

function groupByRound(matches) {
  const grouped = Map.groupBy(matches, (m) =>
    m.side === "grand_final" ? 99 + m.round : m.round
  );
  return Array.from(grouped.entries()).sort((a, b) => a[0] - b[0]);
}

/**
 * Consultation, compte à rebours, inscription et arbre(s) de tournoi avec photos des joueurs.
 */
/** @param {Record<string, any>} props */
export default function TournamentSignupModal({
  tournaments = [],
  shopItems = [],
  currentUserId,
  isAdmin = false,
  onSignup,
  onUnregister,
  onAddBot,
  onGenerateBracket,
  onReportScore,
  onCancelScore,
  onPlaceBet,
  onStartMatch,
  balance = 0,
  onValidateGage,
  onDeleteTournament,
  onOpenCreate,
  onOpenShopAdmin,
  onOpenAdminUsers,
  onClose,
  open,
}) {
  const [idx, setIdx] = useState(0);
  const [view, setView] = useState("info"); // "info" | "bracket"
  const [treeFilter, setTreeFilter] = useState("both"); // "both" | "winners" | "losers"
  const [selectedMatch, setSelectedMatch] = useState(null);
  const [score1, setScore1] = useState(0);
  const [score2, setScore2] = useState(0);
  const [nowMs, setNowMs] = useState(0);
  const autoLaunchedRef = useRef({});

  const safeIdx = tournaments.length ? Math.min(idx, tournaments.length - 1) : 0;
  const t = tournaments[safeIdx] || null;
  const needsCountdown = Boolean(open && t?.status === "registration" && t?.starts_at);

  useEffect(() => {
    if (!needsCountdown) return;
    setNowMs(Date.now());
    const id = setInterval(() => setNowMs(Date.now()), 1000);
    return () => clearInterval(id);
  }, [needsCountdown]);

  useEffect(() => {
    if (!t) return;
    if (t.status === "in_progress" || t.status === "completed") {
      setView("bracket");
    } else {
      setView("info");
    }
    setSelectedMatch(null);
  }, [t?.id, t?.status]);

  const participants = t?.participants || [];
  const registeredCount = t ? t.participant_count ?? participants.length : 0;
  const countdown = needsCountdown ? formatCountdown(t.starts_at, nowMs) : null;

  const playerObjMap = useMemo(
    () => Object.fromEntries(participants.map((p) => [p.user_id, p])),
    [participants]
  );

  const visibleMatches = useMemo(
    () =>
      (t?.matches || []).filter(
        (m) => !m.is_bye && (m.code !== "GF-R" || m.status !== "pending")
      ),
    [t?.matches]
  );

  const winnersRounds = useMemo(
    () =>
      groupByRound(
        visibleMatches.filter((m) => m.side === "winners" || m.side === "grand_final")
      ),
    [visibleMatches]
  );

  const losersRounds = useMemo(
    () => groupByRound(visibleMatches.filter((m) => m.side === "losers")),
    [visibleMatches]
  );

  const activeMatch = useMemo(
    () =>
      (selectedMatch && visibleMatches.find((m) => m.code === selectedMatch.code)) ||
      visibleMatches.find((m) => m.status === "ready") ||
      visibleMatches[0] ||
      null,
    [selectedMatch, visibleMatches]
  );

  // Cotes du match affiché + mes mises dessus, rafraîchies toutes les 5s.
  const [betInfo, setBetInfo] = useState(null); // { code, market, mine: { [playerId]: montant } }
  const [betRefresh, setBetRefresh] = useState(0);
  const betCode =
    open && view === "bracket" && activeMatch?.player1_id && activeMatch?.player2_id
      ? activeMatch.code
      : null;
  const tournamentId = t?.id;

  useEffect(() => {
    if (!betCode || !tournamentId) return;
    let cancelled = false;
    const load = async () => {
      if (document.visibilityState !== "visible") return;
      const [market, myBets] = await Promise.all([
        apiJson(`/api/tournaments/${tournamentId}/matches/${betCode}/bets`).catch(() => null),
        currentUserId ? apiJson("/api/bets/mine").catch(() => null) : Promise.resolve(null),
      ]);
      if (cancelled) return;
      const mine = {};
      for (const b of myBets || []) {
        if (b.tournament_id === tournamentId && b.match_code === betCode && b.status !== "refunded") {
          mine[b.picked_player_id] = (mine[b.picked_player_id] || 0) + b.amount;
        }
      }
      setBetInfo({ code: betCode, market, mine });
    };
    load();
    const id = setInterval(load, 5000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [betCode, tournamentId, currentUserId, betRefresh]);

  const currentBetInfo = betInfo?.code === betCode ? betInfo : null;

  // Lancement automatique de l'arbre quand le compte à rebours atteint 0 (si >= 2 inscrits et admin connecté)
  useEffect(() => {
    if (
      open &&
      t &&
      t.status === "registration" &&
      countdown?.expired &&
      registeredCount >= 2 &&
      isAdmin &&
      !autoLaunchedRef.current[t.id]
    ) {
      autoLaunchedRef.current[t.id] = true;
      onGenerateBracket?.(t);
    }
  }, [open, t, countdown?.expired, registeredCount, isAdmin, onGenerateBracket]);

  if (!t) {
    return (
      <MeleeFrame open={open} onClose={onClose} title="Tournois" caption="Aucun tournoi programmé">
        <div className="mm-center" style={{ gap: "1.8cqw" }}>
          <span className="mm-kicker">Arène Smash BDE</span>
          <span className="mm-big" style={{ fontSize: "4.2cqw" }}>Aucun tournoi actif</span>
          <span className="mm-sub">Reviens bientôt ou demande à un admin de lancer un tournoi !</span>
          <div className="mm-btns" style={{ marginTop: "1.4cqw" }}>
            {isAdmin && (
              <MeleeButton text="Créer un tournoi" selected height={50} onClick={onOpenCreate} />
            )}
            <MeleeButton text="Retour" height={50} onClick={onClose} />
          </div>
        </div>
      </MeleeFrame>
    );
  }

  const getPlayerName = (uid) =>
    uid ? playerObjMap[uid]?.display_name || playerObjMap[uid]?.username || `#${uid}` : "En attente";

  const registered = Boolean(currentUserId && playerObjMap[currentUserId]);
  const maxPlayers = t.max_players || 32;
  const full = registeredCount >= maxPlayers;

  const hasBracket = t.status !== "registration" && visibleMatches.length > 0;
  const hasLosersTree =
    t.has_losers_bracket !== false && losersRounds.length > 0;
  const championName = t.champion_id ? getPlayerName(t.champion_id) : null;

  const handleSelectMatch = (m) => {
    setSelectedMatch(m);
    setScore1(m.score1 ?? 0);
    setScore2(m.score2 ?? 0);
  };

  const renderTree = (rounds, isLosers = false) => (
    <div className="mm-bracket">
      {rounds.map(([roundNum, rMatches]) => (
        <div key={roundNum} className="mm-round">
          <div className="mm-round-title">
            {roundNum >= 100
              ? roundNum === 100
                ? "Grande Finale"
                : "Finale Reset"
              : isLosers
              ? `Losers T${roundNum}`
              : `Tour ${roundNum}`}
          </div>
          {rMatches.map((m) => {
            const p1Obj = m.player1_id ? playerObjMap[m.player1_id] : null;
            const p2Obj = m.player2_id ? playerObjMap[m.player2_id] : null;
            const p1 = getPlayerName(m.player1_id);
            const p2 = getPlayerName(m.player2_id);
            const isReady = m.status === "ready";
            const activeCode =
              selectedMatch?.code ||
              (visibleMatches.find((x) => x.status === "ready") || visibleMatches[0])?.code;
            const isSel = activeCode === m.code;
            const matchGages = m.gages || [];
            const p1Gages = matchGages.filter((g) => g.imposer_id === m.player1_id);
            const p2Gages = matchGages.filter((g) => g.imposer_id === m.player2_id);

            return (
              <button
                key={m.code}
                type="button"
                onClick={() => handleSelectMatch(m)}
                className={`mm-bmatch${isReady ? " mm-bmatch--ready" : ""}${
                  isSel ? " mm-bmatch--selected" : ""
                } mm-bmatch--clickable`}
              >
                <div className="mm-bmatch-head">
                  <span>{m.code}</span>
                  {matchGages.length > 0 && (
                    <span className="mm-bmatch-gagebadge">
                      ★ {matchGages.length} Objet{matchGages.length > 1 ? "s" : ""}
                    </span>
                  )}
                  <span>
                    {m.status === "completed"
                      ? "Terminé"
                      : m.status === "ready"
                      ? "À jouer"
                      : "Attente"}
                  </span>
                </div>
                <div
                  className={`mm-bplayer${
                    m.winner_id && m.winner_id === m.player1_id ? " mm-bplayer--win" : ""
                  }${!m.player1_id ? " mm-bplayer--tbd" : ""}`}
                >
                  <div className="mm-bplayer-info">
                    <PlayerAvatar player={p1Obj} />
                    <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {p1}
                    </span>
                    {p1Gages.map((g) => (
                      <img
                        key={g.id}
                        src={resolveGageImg(g, shopItems)}
                        alt={g.name}
                        title={`${p1} a utilisé ${g.name} : ${g.description}`}
                        className="mm-bitem-icon"
                      />
                    ))}
                  </div>
                  <span>{m.score1 ?? "-"}</span>
                </div>
                <div
                  className={`mm-bplayer${
                    m.winner_id && m.winner_id === m.player2_id ? " mm-bplayer--win" : ""
                  }${!m.player2_id ? " mm-bplayer--tbd" : ""}`}
                >
                  <div className="mm-bplayer-info">
                    <PlayerAvatar player={p2Obj} />
                    <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {p2}
                    </span>
                    {p2Gages.map((g) => (
                      <img
                        key={g.id}
                        src={resolveGageImg(g, shopItems)}
                        alt={g.name}
                        title={`${p2} a utilisé ${g.name} : ${g.description}`}
                        className="mm-bitem-icon"
                      />
                    ))}
                  </div>
                  <span>{m.score2 ?? "-"}</span>
                </div>
              </button>
            );
          })}
        </div>
      ))}
    </div>
  );

  if (view === "bracket" && hasBracket) {
    const oddsOf = (uid) => currentBetInfo?.market?.players?.find((p) => p.user_id === uid);
    // « x1.83 · misé 20 » affiché à côté du nom du joueur
    const betTag = (uid) => {
      if (!currentBetInfo || !uid) return null;
      const odds = oddsOf(uid)?.odds;
      const mine = currentBetInfo.mine[uid] || 0;
      return (
        <span
          style={{
            display: "block",
            fontSize: "clamp(10px, .9cqw, 14px)",
            fontWeight: 800,
            fontStyle: "normal",
            color: "#ffe58a",
          }}
        >
          {odds ? `Cote x${odds}` : "Cote —"}
          {mine > 0 && <span style={{ color: "#4ade80" }}> · Ma mise {fmt(mine)}</span>}
        </span>
      );
    };
    const nameWithBet = (uid) => (
      <span>
        {getPlayerName(uid)}
        {betTag(uid)}
      </span>
    );

    // Pari possible : connecté, match ouvert aux paris, et le joueur n'y participe pas.
    const canBet = Boolean(
      currentUserId &&
        onPlaceBet &&
        activeMatch?.betting_open &&
        activeMatch.player1_id &&
        activeMatch.player2_id &&
        currentUserId !== activeMatch.player1_id &&
        currentUserId !== activeMatch.player2_id
    );
    const betBox = canBet ? (
      <BetBox
        key={`${t.id}-${activeMatch.code}`}
        tournamentId={t.id}
        match={activeMatch}
        getPlayerName={getPlayerName}
        balance={balance}
        market={currentBetInfo?.market}
        onPlaceBet={onPlaceBet}
        onBetPlaced={() => setBetRefresh((n) => n + 1)}
      />
    ) : null;

    return (
      <MeleeFrame
        open={open}
        fullScreen
        onClose={onClose}
        title={t.name}
        sideLabel={isAdmin ? "Score" : "Match"}
        caption={
          championName
            ? `Champion : ${championName} 🏆`
            : `${registeredCount} joueurs · ${
                hasLosersTree ? "2 Arbres (Winners + Losers)" : "Élimination directe"
              }`
        }
      >
        <div className="mm-main" style={{ gap: ".8cqw", paddingRight: "1cqw" }}>
          {hasLosersTree ? (
            <div className="mm-seg">
              <button
                className={treeFilter === "both" ? "on" : ""}
                onClick={() => setTreeFilter("both")}
              >
                Les 2 Arbres
              </button>
              <button
                className={treeFilter === "winners" ? "on" : ""}
                onClick={() => setTreeFilter("winners")}
              >
                Arbre Winners
              </button>
              <button
                className={treeFilter === "losers" ? "on" : ""}
                onClick={() => setTreeFilter("losers")}
              >
                Arbre Losers
              </button>
            </div>
          ) : (
            <span className="mm-label">Arbre du tournoi (Élimination directe)</span>
          )}

          <div className="mm-trees">
            {(!hasLosersTree || treeFilter === "both" || treeFilter === "winners") && (
              <div className="mm-tree-section">
                <div className="mm-tree-header">
                  {hasLosersTree ? "Arbre 1 · Winners Bracket & Finale" : "Arbre Principal"}
                </div>
                {renderTree(winnersRounds, false)}
              </div>
            )}

            {hasLosersTree && (treeFilter === "both" || treeFilter === "losers") && (
              <div className="mm-tree-section">
                <div className="mm-tree-header" style={{ color: "#9aa0ff" }}>
                  Arbre 2 · Losers Bracket
                </div>
                {renderTree(losersRounds, true)}
              </div>
            )}
          </div>

          <div className="mm-btns">
            <MeleeButton text="Infos" height={38} onClick={() => setView("info")} />
            {isAdmin && onDeleteTournament && (
              <MeleeButton
                text="Supprimer"
                height={38}
                onClick={() => onDeleteTournament(t)}
              />
            )}
            <MeleeButton text="Retour" height={38} onClick={onClose} />
          </div>
        </div>

        <Panel>
          {activeMatch ? (
            <>
              <span className="mm-ptag">Match {activeMatch.code}</span>
              <span className="mm-pname" style={{ fontSize: "clamp(14px, 1.45cqw, 24px)" }}>
                {getPlayerName(activeMatch.player1_id)} vs {getPlayerName(activeMatch.player2_id)}
              </span>
              <Sep />
              {isAdmin && (activeMatch.status === "ready" || activeMatch.status === "completed") ? (
                <>
                  <div className="mm-prow" style={{ alignItems: "center" }}>
                    <span style={{ fontSize: "clamp(12px, 1.15cqw, 18px)" }}>
                      {nameWithBet(activeMatch.player1_id)}
                    </span>
                    <input
                      type="number"
                      min={0}
                      max={99}
                      className="mm-field"
                      style={{
                        width: "clamp(52px, 4.5cqw, 76px)",
                        padding: "clamp(4px, .35cqw, 8px) clamp(6px, .5cqw, 10px)",
                        fontSize: "clamp(13px, 1.25cqw, 20px)",
                      }}
                      value={score1}
                      onChange={(e) => setScore1(Number(e.target.value))}
                    />
                  </div>
                  <div className="mm-prow" style={{ alignItems: "center" }}>
                    <span style={{ fontSize: "clamp(12px, 1.15cqw, 18px)" }}>
                      {nameWithBet(activeMatch.player2_id)}
                    </span>
                    <input
                      type="number"
                      min={0}
                      max={99}
                      className="mm-field"
                      style={{
                        width: "clamp(52px, 4.5cqw, 76px)",
                        padding: "clamp(4px, .35cqw, 8px) clamp(6px, .5cqw, 10px)",
                        fontSize: "clamp(13px, 1.25cqw, 20px)",
                      }}
                      value={score2}
                      onChange={(e) => setScore2(Number(e.target.value))}
                    />
                  </div>
                  {betBox}
                  {activeMatch.status === "ready" && onStartMatch && (
                    <MeleeButton
                      text={activeMatch.started_at ? "Delock le match" : "Lock le match"}
                      selected={Boolean(activeMatch.started_at)}
                      height={38}
                      onClick={() =>
                        onStartMatch(t.id, activeMatch.code, !activeMatch.started_at)
                      }
                    />
                  )}
                  {activeMatch.status === "completed" ? (
                    <MeleeButton
                      text="Dévalider"
                      selected
                      height={38}
                      onClick={() => onCancelScore?.(t.id, activeMatch.code)}
                    />
                  ) : (
                    <MeleeButton
                      text="Valider"
                      selected={score1 !== score2}
                      disabled={score1 === score2}
                      height={38}
                      onClick={() =>
                        score1 !== score2 &&
                        onReportScore?.(t.id, activeMatch.code, Number(score1), Number(score2))
                      }
                    />
                  )}
                </>
              ) : (
                <>
                  <PanelRow
                    label={nameWithBet(activeMatch.player1_id)}
                    value={activeMatch.score1 ?? "-"}
                    gold={activeMatch.winner_id && activeMatch.winner_id === activeMatch.player1_id}
                  />
                  <PanelRow
                    label={nameWithBet(activeMatch.player2_id)}
                    value={activeMatch.score2 ?? "-"}
                    gold={activeMatch.winner_id && activeMatch.winner_id === activeMatch.player2_id}
                  />
                  {betBox}
                </>
              )}

              {(activeMatch.gages || []).length > 0 && (
                <>
                  <Sep />
                  <span className="mm-ptag" style={{ color: "#ffd000" }}>
                    Objet{activeMatch.gages.length > 1 ? "s" : ""} utilisé{activeMatch.gages.length > 1 ? "s" : ""}
                  </span>
                  <div className="mm-match-gages">
                    {activeMatch.gages.map((g) => {
                      const rewardVal = g.reward ?? 50;
                      const isDone = g.status === "completed";
                      const isFail = g.status === "failed";
                      return (
                        <div
                          key={g.id}
                          className="mm-match-gage"
                          style={{
                            flexDirection: "column",
                            alignItems: "stretch",
                            gap: ".45cqw",
                            borderColor: isDone
                              ? "rgba(74, 222, 128, .75)"
                              : isFail
                              ? "rgba(248, 113, 113, .65)"
                              : "rgba(255, 208, 0, .55)",
                          }}
                        >
                          <div style={{ display: "flex", alignItems: "center", gap: ".6cqw" }}>
                            <img
                              src={resolveGageImg(g, shopItems)}
                              alt={g.name}
                              className="mm-match-gage-img"
                            />
                            <div className="mm-match-gage-body">
                              <span className="mm-match-gage-title">
                                {g.name} · {getPlayerName(g.imposer_id)}
                              </span>
                              <span className="mm-match-gage-desc">{g.description}</span>
                              <span
                                style={{
                                  fontSize: ".95cqw",
                                  fontWeight: 900,
                                  color: isDone
                                    ? "#4ade80"
                                    : isFail
                                    ? "#f87171"
                                    : "#ffe58a",
                                }}
                              >
                                {isDone
                                  ? `Valide`
                                  : isFail
                                  ? "Invalide"
                                  : `En attente`}
                              </span>
                            </div>
                          </div>

                          {isAdmin && onValidateGage && (
                            <div style={{ display: "flex", gap: ".4cqw" }}>
                              <button
                                type="button"
                                className="mm-field"
                                style={{
                                  flex: 1,
                                  cursor: "pointer",
                                  fontSize: "1.05cqw",
                                  padding: ".35cqw .5cqw",
                                  textAlign: "center",
                                  borderColor: isDone ? "#4ade80" : "#ffd000",
                                  background: isDone
                                    ? "rgba(22, 163, 74, .45)"
                                    : "rgba(255, 208, 0, .18)",
                                  color: "#fff",
                                }}
                                onClick={() => onValidateGage(g.id, true)}
                              >
                                Respecté
                              </button>
                              <button
                                type="button"
                                className="mm-field"
                                style={{
                                  flex: 1,
                                  cursor: "pointer",
                                  fontSize: "1.05cqw",
                                  padding: ".35cqw .5cqw",
                                  textAlign: "center",
                                  borderColor: isFail ? "#f87171" : "#3a42e6",
                                  background: isFail
                                    ? "rgba(220, 38, 38, .42)"
                                    : "rgba(20, 24, 80, .6)",
                                  color: "#fff",
                                }}
                                onClick={() => onValidateGage(g.id, false)}
                              >
                                Échoué
                              </button>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </>
              )}
            </>
          ) : (
            <span className="mm-ptext">Sélectionne un match</span>
          )}
        </Panel>
      </MeleeFrame>
    );
  }

  return (
    <MeleeFrame
      open={open}
      onClose={onClose}
      title="Tournoi"
      sideLabel="Règles"
      caption={`${registeredCount} / ${maxPlayers} joueurs inscrits`}
    >
      <div className="mm-center" style={{ gap: "1cqw" }}>
        {isAdmin && (onOpenCreate || onOpenShopAdmin || onOpenAdminUsers) && (
          <div className="mm-seg" style={{ width: "86%" }}>
            {onOpenCreate && (
              <button type="button" onClick={onOpenCreate}>
                Nouveau Tournoi
              </button>
            )}
            {onOpenShopAdmin && (
              <button type="button" onClick={onOpenShopAdmin}>
                Gérer le Shop
              </button>
            )}
            {onOpenAdminUsers && (
              <button type="button" onClick={onOpenAdminUsers}>
                Joueurs & Tilts
              </button>
            )}
          </div>
        )}
        {tournaments.length > 1 && (
          <div style={{ display: "flex", alignItems: "center", gap: "1.6cqw" }}>
            <button
              className="mm-tri mm-tri--l"
              aria-label="Tournoi précédent"
              onClick={() => setIdx((i) => (i - 1 + tournaments.length) % tournaments.length)}
            />
            <span className="mm-label">
              Tournoi {safeIdx + 1} / {tournaments.length}
            </span>
            <button
              className="mm-tri mm-tri--r"
              aria-label="Tournoi suivant"
              onClick={() => setIdx((i) => (i + 1) % tournaments.length)}
            />
          </div>
        )}
        <span className="mm-kicker">{t.date}</span>
        <span className="mm-big" style={{ fontSize: "4.4cqw" }}>{t.name}</span>

        {countdown && t.status === "registration" && (
          <div className="mm-countdown">
            <span>⏱ {countdown.expired ? "Statut :" : "Début dans :"}</span>
            <span>
              {countdown.expired && registeredCount < 2
                ? `En attente de joueurs (${registeredCount}/2 min.)`
                : countdown.text}
            </span>
          </div>
        )}

        {participants.length > 0 && (
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: ".6cqw",
              justifyContent: "center",
              maxWidth: "92%",
            }}
          >
            {participants.slice(0, 8).map((p) => (
              <span
                key={p.user_id}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: ".4cqw",
                  background: "rgba(20, 24, 80, .65)",
                  border: "1px solid #3a42e6",
                  borderRadius: "999px",
                  padding: ".2cqw .7cqw .2cqw .3cqw",
                  fontSize: "1.3cqw",
                  fontWeight: 700,
                }}
              >
                <PlayerAvatar player={p} />
                <span>{p.display_name || p.username}</span>
              </span>
            ))}
          </div>
        )}

        <div className="mm-btns" style={{ gap: ".8cqw", marginTop: ".6cqw", justifyContent: "center" }}>
          {t.status === "registration" && t.registration_open && (
            registered ? (
              <MeleeButton
                text="Se désinscrire"
                height={40}
                onClick={() => onUnregister?.(t)}
              />
            ) : (
              <MeleeButton
                text="S'inscrire"
                selected={!full}
                disabled={full}
                height={40}
                onClick={() => !full && onSignup?.(t)}
              />
            )
          )}
          {hasBracket && (
            <MeleeButton
              text="Voir l'arbre"
              selected
              height={40}
              onClick={() => setView("bracket")}
            />
          )}
          {isAdmin && t.status === "registration" && !full && (
            <MeleeButton
              text="+ Bot test"
              height={40}
              onClick={() => onAddBot?.(t)}
            />
          )}
          {isAdmin && t.status === "registration" && registeredCount >= 2 && (
            <MeleeButton
              text="Lancer l'arbre"
              selected={registered}
              height={40}
              onClick={() => onGenerateBracket?.(t)}
            />
          )}
          {isAdmin && onDeleteTournament && (
            <MeleeButton
              text="Supprimer"
              height={40}
              onClick={() => onDeleteTournament(t)}
            />
          )}
          <MeleeButton text="Retour" height={40} onClick={onClose} />
        </div>
      </div>
      <Panel>
        {(t.rules || []).map((r, i) => (
          <span key={i} className="mm-ptext" style={{ fontSize: "1.95cqw" }}>
            {r}
          </span>
        ))}
        <Sep />
        <PanelRow
          label="Losers"
          value={t.has_losers_bracket === false ? "Non" : "Oui"}
        />
        <PanelRow label="1er" value={`${t.rewards?.champion ?? 200}`} gold />
      </Panel>
    </MeleeFrame>
  );
}
