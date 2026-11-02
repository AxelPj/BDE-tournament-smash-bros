import MeleeFrame, { Panel, PanelRow, Sep } from "../ui/MeleeFrame";
import MeleeButton from "../ui/MeleeButton";
import { fmt } from "./ShopModal";

/**
 * Profil d'un joueur. Les infos viennent de ton back (ex : /v2/me de l'API 42 + tes stats).
 * Props : player { login, campus, avatar, wins, losses, tournaments, rank, balance }, onClose, open
 * Le taux de victoire est calculé et affiché façon « pourcentage de dégâts ».
 */
export default function ProfileModal({ player: p, onAvatarClick, onOpenInventory, onClose, open }) {
  if (!p) return null;
  const total = (p.wins || 0) + (p.losses || 0);
  const rate = total ? Math.round((p.wins / total) * 100) : 0;
  return (
    <MeleeFrame open={open} onClose={onClose} title="Profil" sideLabel="Stats" caption={p.rank ? `Rang #${p.rank}` : p.login}>
      <div className="mm-main" style={{ gap: "1.8cqw" }}>
        <div className="mm-split" style={{ paddingLeft: 0 }}>
          <button
            type="button"
            className="mm-avatar"
            title="Cliquer pour choisir ton combattant (84 persos)"
            onClick={onAvatarClick}
            style={{
              cursor: "pointer",
              padding: 0,
              background: p.avatarColor
                ? `radial-gradient(circle at 50% 45%, ${p.avatarColor}, color-mix(in srgb, ${p.avatarColor} 38%, #0a0c28))`
                : undefined,
              position: "relative",
            }}
          >
            {p.avatar ? (
              <img src={p.avatar} alt={p.login} />
            ) : (
              <div className="mm-ph" style={{ border: 0 }}>
                avatar
              </div>
            )}
            <span className="mm-avatar-edit">✎ Choisir perso</span>
          </button>
          <div style={{ display: "flex", flexDirection: "column", gap: ".8cqw", alignItems: "flex-start", minWidth: 0 }}>
            <span
              style={{
                fontStyle: "italic",
                fontWeight: 900,
                fontSize:
                  (p.login || "").length > 14
                    ? "2.6cqw"
                    : (p.login || "").length > 10
                    ? "3.3cqw"
                    : "4.2cqw",
                lineHeight: 1.05,
                maxWidth: "100%",
                overflowWrap: "break-word",
              }}
            >
              {p.login}
            </span>
            <span
              style={{
                fontWeight: 600,
                fontSize: "1.8cqw",
                color: "#9aa0ff",
                maxWidth: "100%",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {p.campus}
            </span>
            <div className="mm-percent" style={{ marginTop: "1.2cqw" }}><b>{rate}</b><i>%</i></div>
            <span className="mm-label" style={{ fontSize: "1.4cqw", color: "#c3c6d6" }}>Taux de victoire</span>
          </div>
        </div>
        <div className="mm-btns">
          {onOpenInventory && (
            <MeleeButton text="Inventaire" selected height={42} onClick={onOpenInventory} />
          )}
          <MeleeButton text="Retour" height={42} onClick={onClose} />
        </div>
      </div>
      <Panel>
        <PanelRow label="Tilts" value={fmt(p.balance ?? 0)} gold />
        <Sep />
        <PanelRow label="Victoires" value={p.wins ?? 0} />
        <PanelRow label="Défaites" value={p.losses ?? 0} />
        <PanelRow label="Tournois" value={p.tournaments ?? 0} />
      </Panel>
    </MeleeFrame>
  );
}
