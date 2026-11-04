import { useState } from "react";
import MeleeFrame, { Panel, PanelRow, Sep, ItemImage } from "../ui/MeleeFrame";
import MeleeButton from "../ui/MeleeButton";
import { fmt } from "../../lib/utils";

export { fmt };

/**
 * Shop : grille d'objets-gages, détail de l'objet sélectionné à droite.
 * Props : items [{ id, name, gage, price, gain, image }], balance, onBuy(item), onClose, open
 */
/** @param {Record<string, any>} props */
export default function ShopModal({ items = [], balance = 0, isAdmin = false, onAdminShop, onBuy, onClose, open }) {
  const [sel, setSel] = useState(0);
  const it = items[sel];
  const canBuy = it && balance >= it.price;
  return (
    <MeleeFrame open={open} onClose={onClose} title="Shop" sideLabel="Objet" caption={`Solde : ${fmt(balance)} Tilts`}>
      <div className="mm-main">
        <div className="mm-grid mm-shop-grid">
          {items.map((o, i) => (
            <button key={o.id ?? i} className={`mm-tile${i === sel ? " mm-tile--on" : ""}`} onClick={() => setSel(i)}>
              <ItemImage src={o.image} alt={o.name} selected={i === sel} />
              <span className="mm-tile-name">{o.name}</span>
              <span className="mm-tile-sub">
                {o.price === 0 ? `Gratuit · +${fmt(o.gain)} Tilts` : `${fmt(o.price)} Tilts`}
              </span>
            </button>
          ))}
        </div>
        <div className="mm-btns">
          <MeleeButton
            text="Acheter"
            selected={Boolean(canBuy)}
            disabled={!canBuy}
            height={40}
            onClick={() => canBuy && onBuy?.(it)}
          />
          {isAdmin && (
            <MeleeButton text="Gérer Shop" height={40} onClick={onAdminShop} />
          )}
          <MeleeButton text="Retour" height={40} onClick={onClose} />
        </div>
      </div>
      {it && (
        <Panel>
          <span className="mm-pname">{it.name}</span>
          <span className="mm-ptag">
            {it.price === 0 ? "Gage à soi-même" : "Gage"}
          </span>
          <span className="mm-ptext">{it.gage}</span>
          <Sep />
          <PanelRow label="Prix" value={it.price === 0 ? "Gratuit" : `${fmt(it.price)} Tilts`} />
          <PanelRow label="Gain (validé)" value={`+${fmt(it.gain)} Tilts`} gold />
        </Panel>
      )}
    </MeleeFrame>
  );
}
