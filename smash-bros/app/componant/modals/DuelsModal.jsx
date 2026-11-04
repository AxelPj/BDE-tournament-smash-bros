import { useEffect, useMemo, useState } from "react";
import MeleeFrame, { Panel, PanelRow, Sep } from "../ui/MeleeFrame";
import MeleeButton from "../ui/MeleeButton";
import BetBox, { BetTag, useBetMarket } from "../ui/BetBox";
import PlayerAvatar from "../ui/PlayerAvatar";
import { apiJson } from "../../lib/utils";

const STATUS_LABELS = {
  pending: "En attente de réponse",
  accepted: "En attente d'un admin",
  validated: "Paris ouverts",
  in_progress: "Locké · paris fermés",
  completed: "Terminé",
  refused: "Refusé",
  cancelled: "Annulé",
};

const ACTIVE = ["pending", "accepted", "validated", "in_progress"];

const playerName = (p) => p?.display_name || p?.username || "?";

const scoreInputStyle = {
  width: "clamp(52px, calc(4.5 * var(--u)), 76px)",
  padding: "clamp(4px, calc(.35 * var(--u)), 8px) clamp(6px, calc(.5 * var(--u)), 10px)",
  fontSize: "clamp(13px, calc(1.25 * var(--u)), 20px)",
};

const cardGridStyle = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fill, minmax(clamp(155px, calc(12.8 * var(--u)), 235px), 1fr))",
  gap: "clamp(8px, calc(.7 * var(--u)), 14px)",
};

/**
 * Duels : défier n'importe quel joueur, répondre aux défis, et pour les admins
 * confirmer, locker, valider/dévalider. Un duel confirmé se joue comme un match
 * de tournoi (paris, lock, validation), sans objet.
 */
/** @param {Record<string, any>} props */
export default function DuelsModal({
  open,
  onClose,
  duels = [],
  currentUserId,
  isAdmin = false,
  balance = 0,
  onChallenge,
  onRespond,
  onCancelDuel,
  onValidateDuel,
  onLockDuel,
  onReportResult,
  onCancelResult,
  onPlaceBet,
}) {
  const [tab, setTab] = useState("matches"); // "matches" | "challenge"
  const [selectedId, setSelectedId] = useState(null);
  const [search, setSearch] = useState("");
  const [candidates, setCandidates] = useState([]);
  const [challengeMsg, setChallengeMsg] = useState(null); // { ok, text }
  const [score1, setScore1] = useState(0);
  const [score2, setScore2] = useState(0);

  // Recherche de joueurs à défier (avec un petit délai pendant la frappe)
  useEffect(() => {
    if (!open) return;
    const id = setTimeout(async () => {
      const users = await apiJson(`/api/users?search=${encodeURIComponent(search.trim())}`).catch(
        () => null
      );
      setCandidates((users || []).filter((u) => u.id !== currentUserId));
    }, 250);
    return () => clearTimeout(id);
  }, [open, search, currentUserId]);

  const visibleDuels = useMemo(
    () => duels.filter((d) => d.status !== "refused" && d.status !== "cancelled"),
    [duels]
  );
  const groups = useMemo(
    () => [
      {
        title: "Défis en attente",
        items: visibleDuels.filter((d) => d.status === "pending" || d.status === "accepted"),
      },
      {
        title: "Duels confirmés",
        items: visibleDuels.filter((d) => d.status === "validated" || d.status === "in_progress"),
      },
      { title: "Terminés", items: visibleDuels.filter((d) => d.status === "completed").slice(0, 10) },
    ],
    [visibleDuels]
  );

  const duel =
    visibleDuels.find((d) => d.id === selectedId) ||
    visibleDuels.find((d) => d.status === "validated" || d.status === "in_progress") ||
    visibleDuels[0] ||
    null;

  const confirmed = duel && ["validated", "in_progress", "completed"].includes(duel.status);
  const challengerId = duel?.challenger.id;
  const opponentId = duel?.opponent.id;
  const isPlayer = duel && (currentUserId === challengerId || currentUserId === opponentId);
  const getPlayerName = (uid) =>
    uid === challengerId ? playerName(duel.challenger) : playerName(duel?.opponent);

  const duelId = duel?.id;
  const bets = useBetMarket(
    open && confirmed ? `/api/duels/${duelId}/bets` : null,
    (b) => b.duel_id === duelId,
    currentUserId
  );

  const selectDuel = (d) => {
    setSelectedId(d.id);
    setScore1(d.challenger_score ?? 0);
    setScore2(d.opponent_score ?? 0);
  };

  // Un seul défi lancé à la fois
  const myActiveChallenge = duels.find(
    (d) => d.challenger.id === currentUserId && ACTIVE.includes(d.status)
  );

  const challenge = async (target) => {
    setChallengeMsg(null);
    const res = await onChallenge?.(target.id);
    setChallengeMsg(
      res?.ok
        ? { ok: true, text: `Défi envoyé à ${playerName(target)} !` }
        : { ok: false, text: res?.error || "Défi refusé" }
    );
    if (res?.ok) setTab("matches");
  };

  // Carte d'un duel, même rendu que les matchs de l'arbre du tournoi
  const renderCard = (d) => {
    const mine = d.challenger.id === currentUserId || d.opponent.id === currentUserId;
    const row = (player, score) => (
      <div className={`mm-bplayer${d.winner_id && d.winner_id === player.id ? " mm-bplayer--win" : ""}`}>
        <div className="mm-bplayer-info">
          <PlayerAvatar player={player} />
          <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {playerName(player)}
          </span>
        </div>
        <span>{score ?? "-"}</span>
      </div>
    );
    return (
      <button
        key={d.id}
        type="button"
        onClick={() => selectDuel(d)}
        className={`mm-bmatch mm-bmatch--clickable${d.betting_open ? " mm-bmatch--ready" : ""}${
          duel?.id === d.id ? " mm-bmatch--selected" : ""
        }`}
      >
        <div className="mm-bmatch-head">
          <span>
            {mine ? "★ " : ""}Duel #{d.id}
          </span>
          <span>{STATUS_LABELS[d.status]}</span>
        </div>
        {row(d.challenger, d.challenger_score)}
        {row(d.opponent, d.opponent_score)}
      </button>
    );
  };

  const nameWithBet = (uid) => (
    <span>
      {getPlayerName(uid)}
      {confirmed && <BetTag market={bets.market} mine={bets.mine} playerId={uid} />}
    </span>
  );

  const betBox =
    duel && duel.betting_open && currentUserId && !isPlayer && onPlaceBet ? (
      <BetBox
        key={`duel-${duel.id}`}
        players={[challengerId, opponentId]}
        getPlayerName={getPlayerName}
        balance={balance}
        market={bets.market}
        onPlaceBet={(pick, amount) => onPlaceBet(duel.id, pick, amount)}
        onBetPlaced={bets.refresh}
      />
    ) : null;

  const renderPanel = () => {
    if (!duel) return <span className="mm-ptext">Aucun duel pour l&apos;instant</span>;
    const waitingText = (text) => (
      <span className="mm-ptext" style={{ fontSize: "clamp(12px, calc(1.2 * var(--u)), 18px)" }}>
        {text}
      </span>
    );

    return (
      <>
        <span className="mm-ptag">Duel #{duel.id} · {STATUS_LABELS[duel.status] || duel.status}</span>
        <span className="mm-pname" style={{ fontSize: "clamp(14px, calc(1.45 * var(--u)), 24px)" }}>
          {playerName(duel.challenger)} vs {playerName(duel.opponent)}
        </span>
        <Sep />

        {duel.status === "pending" &&
          (currentUserId === opponentId ? (
            <>
              {waitingText(`${playerName(duel.challenger)} te défie !`)}
              <div style={{ display: "flex", flexDirection: "column", gap: "calc(.4 * var(--u))" }}>
                <MeleeButton text="Accepter" selected height={38} onClick={() => onRespond?.(duel.id, true)} />
                <MeleeButton text="Refuser" height={38} onClick={() => onRespond?.(duel.id, false)} />
              </div>
            </>
          ) : currentUserId === challengerId ? (
            <>
              {waitingText(`En attente de la réponse de ${playerName(duel.opponent)}`)}
              <MeleeButton text="Annuler le défi" height={38} onClick={() => onCancelDuel?.(duel)} />
            </>
          ) : (
            waitingText(`En attente de la réponse de ${playerName(duel.opponent)}`)
          ))}

        {duel.status === "accepted" &&
          (isAdmin ? (
            <MeleeButton
              text="Confirmer le duel"
              selected
              height={38}
              onClick={() => onValidateDuel?.(duel.id)}
            />
          ) : (
            waitingText("Défi accepté · en attente de confirmation par un admin")
          ))}

        {confirmed &&
          (isAdmin ? (
            <>
              <div className="mm-prow" style={{ alignItems: "center" }}>
                <span style={{ fontSize: "clamp(12px, calc(1.15 * var(--u)), 18px)" }}>{nameWithBet(challengerId)}</span>
                <input
                  type="number"
                  min={0}
                  max={99}
                  className="mm-field"
                  style={scoreInputStyle}
                  value={score1}
                  onChange={(e) => setScore1(Number(e.target.value))}
                />
              </div>
              <div className="mm-prow" style={{ alignItems: "center" }}>
                <span style={{ fontSize: "clamp(12px, calc(1.15 * var(--u)), 18px)" }}>{nameWithBet(opponentId)}</span>
                <input
                  type="number"
                  min={0}
                  max={99}
                  className="mm-field"
                  style={scoreInputStyle}
                  value={score2}
                  onChange={(e) => setScore2(Number(e.target.value))}
                />
              </div>
              {betBox}
              {duel.status !== "completed" && (
                <MeleeButton
                  text={duel.status === "in_progress" ? "Delock le match" : "Lock le match"}
                  selected={duel.status === "in_progress"}
                  height={38}
                  onClick={() => onLockDuel?.(duel.id, duel.status === "validated")}
                />
              )}
              {duel.status === "completed" ? (
                <MeleeButton text="Dévalider" selected height={38} onClick={() => onCancelResult?.(duel)} />
              ) : (
                <MeleeButton
                  text="Valider"
                  selected={score1 !== score2}
                  disabled={score1 === score2}
                  height={38}
                  onClick={() =>
                    score1 !== score2 && onReportResult?.(duel.id, Number(score1), Number(score2))
                  }
                />
              )}
            </>
          ) : (
            <>
              <PanelRow
                label={nameWithBet(challengerId)}
                value={duel.challenger_score ?? "-"}
                gold={duel.winner_id === challengerId}
              />
              <PanelRow
                label={nameWithBet(opponentId)}
                value={duel.opponent_score ?? "-"}
                gold={duel.winner_id === opponentId}
              />
              {betBox}
            </>
          ))}

        {isAdmin && ACTIVE.includes(duel.status) && (
          <>
            <Sep />
            <MeleeButton text="Annuler le duel" height={34} onClick={() => onCancelDuel?.(duel)} />
          </>
        )}
      </>
    );
  };

  return (
    <MeleeFrame
      open={open}
      fullScreen
      onClose={onClose}
      title="Duels"
      sideLabel="Duel"
      caption="Défie n'importe quel joueur · le défi doit être accepté puis confirmé par un admin"
    >
      <div className="mm-main" style={{ gap: "calc(.8 * var(--u))", paddingRight: "calc(1 * var(--u))" }}>
        <div className="mm-seg">
          <button className={tab === "matches" ? "on" : ""} onClick={() => setTab("matches")}>
            Matchs
          </button>
          <button className={tab === "challenge" ? "on" : ""} onClick={() => setTab("challenge")}>
            Défier un joueur
          </button>
        </div>

        {tab === "matches" && challengeMsg?.ok && (
          <span style={{ fontWeight: 800, color: "#4ade80" }}>{challengeMsg.text}</span>
        )}

        {tab === "matches" && (
          <div className="mm-trees">
            {visibleDuels.length === 0 && (
              <span className="mm-sub">Aucun duel pour l&apos;instant : lance un défi !</span>
            )}
            {groups.map(
              (g) =>
                g.items.length > 0 && (
                  <div key={g.title} className="mm-tree-section">
                    <div className="mm-tree-header">{g.title}</div>
                    <div style={cardGridStyle}>{g.items.map(renderCard)}</div>
                  </div>
                )
            )}
          </div>
        )}

        {tab === "challenge" && (
          <div className="mm-trees">
            <div className="mm-tree-section">
              <div className="mm-tree-header">Défier un joueur</div>
              {myActiveChallenge ? (
                <span className="mm-sub">
                  Tu as déjà un défi en cours contre {playerName(myActiveChallenge.opponent)} : attends
                  qu&apos;il soit terminé, refusé ou annulé.
                </span>
              ) : (
                <>
                  <input
                    type="text"
                    className="mm-field"
                    placeholder="Rechercher un joueur…"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    style={{ fontSize: "clamp(13px, calc(1.2 * var(--u)), 18px)" }}
                  />
                  <div style={cardGridStyle}>
                    {candidates.slice(0, 24).map((u) => (
                      <button
                        key={u.id}
                        type="button"
                        className="mm-bmatch mm-bmatch--clickable"
                        onClick={() => challenge(u)}
                      >
                        <div className="mm-bplayer">
                          <div className="mm-bplayer-info">
                            <PlayerAvatar player={u} />
                            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                              {playerName(u)}
                            </span>
                          </div>
                          <span>⚔</span>
                        </div>
                      </button>
                    ))}
                  </div>
                  {candidates.length === 0 && <span className="mm-sub">Aucun joueur trouvé</span>}
                </>
              )}
              {challengeMsg && (
                <span style={{ fontWeight: 800, color: challengeMsg.ok ? "#4ade80" : "#f87171" }}>
                  {challengeMsg.text}
                </span>
              )}
            </div>
          </div>
        )}

        <div className="mm-btns">
          <MeleeButton text="Retour" height={38} onClick={onClose} />
        </div>
      </div>

      <Panel>{renderPanel()}</Panel>
    </MeleeFrame>
  );
}
