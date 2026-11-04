import { useState } from "react";
import MeleeFrame, { Panel, PanelRow, Sep, ItemImage } from "../ui/MeleeFrame";
import MeleeButton from "../ui/MeleeButton";
import { fmt } from "./ShopModal";

/**
 * Inventaire : objets possédés (avec quantité). « Utiliser » ouvre le choix du combat.
 * Props : items [{ id, name, gage, gain, qty, image }], slots (9), onUse(item), onClose, open
 */
/** @param {Record<string, any>} props */
export default function InventoryModal({ items = [], slots = 9, onUse, onClose, open }) {
  const [sel, setSel] = useState(0);
  const it = items[sel];
  const shown = items.slice(0, 6);
  const empties = Math.max(0, 6 - shown.length);
  return (
    <MeleeFrame open={open} onClose={onClose} title="Inventaire" sideLabel="Objet" caption={`${items.length} / ${slots} emplacements`}>
      <div className="mm-main">
        <div className="mm-grid">
          {shown.map((o, i) => (
            <button key={o.id ?? i} className={`mm-tile${i === sel ? " mm-tile--on" : ""}`} onClick={() => setSel(i)}>
              <ItemImage src={o.image} alt={o.name} selected={i === sel} />
              <span className="mm-tile-name">{o.name}</span>
              <span className="mm-tile-sub">+{fmt(o.gain)}</span>
              {o.qty > 1 && <span className="mm-qty">×{o.qty}</span>}
            </button>
          ))}
          {Array.from({ length: empties }, (_, i) => <div key={"e" + i} className="mm-empty" />)}
        </div>
        <div className="mm-btns">
          <MeleeButton text="Utiliser" selected={!!it} disabled={!it} height={40} onClick={() => it && onUse?.(it)} />
          <MeleeButton text="Retour" height={40} onClick={onClose} />
        </div>
      </div>
      {it ? (
        <Panel>
          <span className="mm-pname">{it.name}</span>
          <span className="mm-ptag">Gage</span>
          <span className="mm-ptext">{it.gage}</span>
          <Sep />
          <PanelRow label="Gain" value={`+${fmt(it.gain)} Tilts`} gold />
          <PanelRow label="Restants" value={`×${it.qty ?? 1}`} />
        </Panel>
      ) : (
        <Panel><span className="mm-ptext">Inventaire vide. Passe au Shop !</span></Panel>
      )}
    </MeleeFrame>
  );
}
