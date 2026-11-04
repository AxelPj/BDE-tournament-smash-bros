import { useEffect, useState } from "react";
import MeleeFrame, { Panel, PanelRow, Sep } from "../ui/MeleeFrame";
import MeleeButton from "../ui/MeleeButton";
import { fmt } from "../../lib/utils";

/**
 * Classement général des joueurs (Stats).
 * Affiche tous les joueurs classés par victoires puis solde de Tilts,
 * avec la fiche détaillée du joueur sélectionné dans le panneau de droite.
 */
/** @param {Record<string, any>} props */
export default function LeaderboardModal({
  open,
  onClose,
  players = [],
  currentUserId,
  isAdmin = false,
  onOpenAdminUsers,
}) {
  const [selIdx, setSelIdx] = useState(0);

  const realPlayers = players
    .filter((pl) => !/^(bot_|cpu_|pnj_)/i.test(pl?.login || ""))
    .map((pl, idx) => ({ ...pl, rank: idx + 1 }));

  useEffect(() => {
    if (!open || !realPlayers.length) return;
    const myIdx = realPlayers.findIndex((p) => p.id === currentUserId);
    setSelIdx(myIdx >= 0 ? myIdx : 0);
  }, [open, realPlayers.length, currentUserId]);

  const p = realPlayers[selIdx] || realPlayers[0] || null;
  const total = p ? (p.wins || 0) + (p.losses || 0) : 0;
  const rate = total ? Math.round((p.wins / total) * 100) : 0;

  return (
    <MeleeFrame
      open={open}
      onClose={onClose}
      title="Classement"
      sideLabel="Stats"
      caption={`${realPlayers.length} joueur${realPlayers.length > 1 ? "s" : ""} classé${realPlayers.length > 1 ? "s" : ""}`}
    >
      <div className="mm-main" style={{ gap: ".8cqw", padding: "0 1cqw 0 2cqw" }}>
        <span className="mm-label">Classement Général BDE</span>

        <div
          className="mm-list"
          style={{
            maxHeight: "30cqw",
            overflowY: "auto",
            paddingRight: ".4cqw",
          }}
        >
          {realPlayers.map((pl, i) => {
            const isSel = i === selIdx;
            const isMe = pl.id === currentUserId;
            const plTotal = (pl.wins || 0) + (pl.losses || 0);
            const plRate = plTotal ? Math.round((pl.wins / plTotal) * 100) : 0;
            const avatarSrc =
              pl.avatar_url ||
              (pl.login ? `https://cdn.intra.42.fr/users/${pl.login}.jpg` : null);
            const medal =
              pl.rank === 1 ? "🥇" : pl.rank === 2 ? "🥈" : pl.rank === 3 ? "🥉" : `#${pl.rank}`;

            return (
              <button
                key={pl.id ?? pl.login}
                type="button"
                className={`mm-match${isSel ? " mm-on" : ""}`}
                style={{ padding: ".7cqw 1.1cqw" }}
                onClick={() => setSelIdx(i)}
              >
                <div style={{ display: "flex", alignItems: "center", gap: ".9cqw", minWidth: 0 }}>
                  <span
                    style={{
                      fontWeight: 900,
                      fontStyle: "italic",
                      fontSize: "1.65cqw",
                      minWidth: "2.8cqw",
                      color: pl.rank <= 3 ? "#ffe58a" : "#9aa0ff",
                    }}
                  >
                    {medal}
                  </span>
                  <span className="mm-bavatar" style={{ width: "2.8cqw", height: "2.8cqw" }}>
                    {avatarSrc ? (
                      <img src={avatarSrc} alt={pl.display_name || pl.login} />
                    ) : (
                      (pl.display_name || pl.login || "?").charAt(0).toUpperCase()
                    )}
                  </span>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div
                      className="mm-match-title"
                      style={{
                        fontSize: "1.75cqw",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {pl.display_name || pl.login}
                      {isMe ? " (Toi)" : ""}
                    </div>
                    <div className="mm-match-info" style={{ fontSize: "1.25cqw" }}>
                      {pl.wins}V · {pl.losses}D ({plRate}%) · {fmt(pl.balance)} Tilts
                    </div>
                  </div>
                </div>
                <span className="mm-tri mm-tri--l" />
              </button>
            );
          })}
        </div>

        <div className="mm-btns">
          {isAdmin && onOpenAdminUsers && (
            <MeleeButton text="Gérer Joueurs" selected height={38} onClick={onOpenAdminUsers} />
          )}
          <MeleeButton text="Retour" height={38} onClick={onClose} />
        </div>
      </div>

      {p ? (
        <Panel>
          <span className="mm-ptag">Rang #{p.rank}</span>
          <span
            className="mm-pname"
            style={{
              fontSize: "2.1cqw",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {p.display_name || p.login}
          </span>
          <div className="mm-percent" style={{ margin: ".2cqw 0" }}>
            <b style={{ fontSize: "5.2cqw" }}>{rate}</b>
            <i style={{ fontSize: "2.5cqw" }}>%</i>
          </div>
          <Sep />
          <PanelRow label="Tilts" value={fmt(p.balance ?? 0)} gold />
          <PanelRow label="Victoires" value={p.wins ?? 0} />
          <PanelRow label="Défaites" value={p.losses ?? 0} />
          <PanelRow label="Tournois" value={p.tournaments ?? 0} />
        </Panel>
      ) : (
        <Panel>
          <span className="mm-ptext">Aucun joueur inscrit</span>
        </Panel>
      )}
    </MeleeFrame>
  );
}
