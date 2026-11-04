import { useEffect, useState } from "react";
import MeleeFrame, { Panel, PanelRow, Sep, ItemImage } from "../ui/MeleeFrame";
import MeleeButton from "../ui/MeleeButton";
import { fmt } from "./ShopModal";

/**
 * Choix du combat où utiliser un objet.
 * Props : item, matches [{ id, opponent, info, disabled }], onConfirm(item, match), onBack, onClose, open
 */
/** @param {Record<string, any>} props */
export default function UseItemModal({ item, matches = [], onConfirm, onBack, onClose, open }) {
  const first = matches.findIndex((x) => !x.disabled);
  const [sel, setSel] = useState(first < 0 ? null : first);

  useEffect(() => {
    if (!open) return;
    const idx = matches.findIndex((x) => !x.disabled);
    setSel(idx < 0 ? null : idx);
  }, [open, matches]);

  const m = sel != null && matches[sel] && !matches[sel].disabled ? matches[sel] : null;
  if (!item) return null;
  return (
    <MeleeFrame open={open} onClose={onClose} title="Utiliser" sideLabel="Équipé" caption="1 objet par combat">
      <div className="mm-main" style={{ gap: "calc(1 * var(--u))" }}>
        <span className="mm-label">Choisis ton combat</span>
        <div className="mm-list">
          {matches.length === 0 ? (
            <span className="mm-sub" style={{ padding: "calc(1.4 * var(--u)) 0" }}>
              Aucun combat jouable en attente. Inscris-toi à un tournoi ou lance un duel !
            </span>
          ) : (
            matches.map((x, i) => (
              <button key={x.id ?? i} disabled={x.disabled} className={`mm-match${i === sel && !x.disabled ? " mm-on" : ""}`} onClick={() => !x.disabled && setSel(i)}>
                <div>
                  <div className="mm-match-title">vs. {x.opponent}</div>
                  <div className="mm-match-info">{x.info}</div>
                </div>
                <span className="mm-tri mm-tri--l" />
              </button>
            ))
          )}
        </div>
        <div className="mm-btns" style={{ marginTop: "calc(.8 * var(--u))" }}>
          <MeleeButton text="Retour" mirror height={46} onClick={onBack ?? onClose} />
          <MeleeButton text="Confirmer" selected={!!m} disabled={!m} height={46} onClick={() => m && onConfirm?.(item, m)} />
        </div>
      </div>
      <Panel center>
        <ItemImage src={item.image} alt={item.name} selected />
        <span className="mm-pname">{item.name}</span>
        <span className="mm-ptag">
          {item.price === 0 ? "Gage à soi-même" : "Objet équipé"}
        </span>
        <span className="mm-ptext">{item.gage}</span>
        <Sep />
        <PanelRow label="Gain (validé)" value={`+${fmt(item.gain)} Tilts`} gold />
      </Panel>
    </MeleeFrame>
  );
}
