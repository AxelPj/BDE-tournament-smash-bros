import { useEffect, useState } from "react";
import MeleeFrame, { Panel, ItemImage, Sep } from "../ui/MeleeFrame";
import MeleeButton from "../ui/MeleeButton";
import { fmt } from "./ShopModal";

/**
 * Administration de la boutique :
 * - Choisir quels objets sont affichés au Shop (is_available)
 * - Modifier leur sprite (parmi les 87 sprites officiels Smash Bros), nom, définition (gage) et prix
 * - Créer un nouvel objet ou archiver un objet existant
 */
/** @param {Record<string, any>} props */
export default function ShopAdminModal({
  open,
  onClose,
  onOpenTournamentCreate,
  onOpenAdminUsers,
  gages = [],
  sprites = [],
  onSaveGage,
  onCreateGage,
  onArchiveGage,
}) {
  const [selId, setSelId] = useState(null); // id du gage sélectionné ou "new"
  const [pickingSprite, setPickingSprite] = useState(false);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState(300);
  const [reward, setReward] = useState(50);
  const [imageUrl, setImageUrl] = useState("/items/item_list29.png");
  const [isAvailable, setIsAvailable] = useState(true);

  const currentGage =
    selId === "new"
      ? null
      : gages.find((g) => g.id === selId) || gages[0] || null;

  useEffect(() => {
    if (!open) return;
    if (selId === "new") {
      setName("");
      setDescription("");
      setPrice(0);
      setReward(100);
      setImageUrl(sprites[0]?.url || "/items/item_list29.png");
      setIsAvailable(true);
    } else if (currentGage) {
      setSelId(currentGage.id);
      setName(currentGage.name || "");
      setDescription(currentGage.description || "");
      setPrice(currentGage.price ?? 300);
      setReward(currentGage.reward ?? 50);
      setImageUrl(currentGage.image_url || "/items/item_list29.png");
      setIsAvailable(!!currentGage.is_available);
    }
  }, [open, selId, currentGage?.id]);

  const activeCount = gages.filter((g) => g.is_available).length;

  const handleSelectSprite = (sp) => {
    setImageUrl(sp.url);
    if (!name.trim() || selId === "new") {
      setName(sp.name);
    }
    setPickingSprite(false);
  };

  const handleSave = async () => {
    if (!name.trim()) return;
    const payload = {
      name: name.trim(),
      description: description.trim(),
      price: Math.max(0, Number(price) || 0),
      reward: Math.max(0, Number(reward) || 0),
      image_url: imageUrl,
      is_available: isAvailable,
    };
    if (selId === "new" || !currentGage) {
      const created = await onCreateGage?.(payload);
      if (created?.id) setSelId(created.id);
    } else {
      await onSaveGage?.(currentGage.id, payload);
    }
  };

  if (pickingSprite) {
    return (
      <MeleeFrame
        open={open}
        onClose={() => setPickingSprite(false)}
        title="Choisir un Sprite"
        caption={`${sprites.length} objets officiels Super Smash Bros.`}
      >
        <div className="mm-main" style={{ gap: "1.2cqw" }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(6, minmax(0, 1fr))",
              gap: "1cqw",
              maxHeight: "34cqw",
              overflowY: "auto",
              padding: ".6cqw",
            }}
          >
            {sprites.map((sp) => (
              <button
                key={sp.url + sp.name}
                type="button"
                className={`mm-tile${imageUrl === sp.url ? " mm-tile--on" : ""}`}
                style={{ alignItems: "center", textAlign: "center", padding: ".6cqw" }}
                onClick={() => handleSelectSprite(sp)}
              >
                <ItemImage src={sp.url} alt={sp.name} selected={imageUrl === sp.url} />
                <span className="mm-tile-name" style={{ fontSize: "1.15cqw" }}>
                  {sp.name}
                </span>
              </button>
            ))}
          </div>
          <div className="mm-btns">
            <MeleeButton text="Retour" mirror height={44} onClick={() => setPickingSprite(false)} />
          </div>
        </div>
      </MeleeFrame>
    );
  }

  return (
    <MeleeFrame
      open={open}
      onClose={onClose}
      title="Admin · Shop"
      sideLabel="Éditer"
      caption={`${activeCount} / 6 objets actifs au Shop`}
    >
      <div className="mm-main" style={{ gap: ".8cqw", padding: "0 1cqw 0 2cqw" }}>
        {(onOpenTournamentCreate || onOpenAdminUsers) && (
          <div className="mm-seg" style={{ marginBottom: ".2cqw" }}>
            {onOpenTournamentCreate && (
              <button type="button" onClick={onOpenTournamentCreate}>
                Nouveau Tournoi
              </button>
            )}
            <button type="button" className="on">
              Gérer le Shop
            </button>
            {onOpenAdminUsers && (
              <button type="button" onClick={onOpenAdminUsers}>
                Joueurs & Tilts
              </button>
            )}
          </div>
        )}

        <div
          className="mm-grid"
          style={{
            maxHeight: "25cqw",
            overflowY: "auto",
            paddingRight: ".4cqw",
          }}
        >
          {gages.map((g) => {
            const isSel = selId !== "new" && currentGage?.id === g.id;
            return (
              <button
                key={g.id}
                type="button"
                className={`mm-tile${isSel ? " mm-tile--on" : ""}`}
                style={{ opacity: g.is_available ? 1 : 0.5 }}
                onClick={() => setSelId(g.id)}
              >
                <ItemImage src={g.image_url} alt={g.name} selected={isSel} />
                <span className="mm-tile-name">{g.name}</span>
                <span className="mm-tile-sub">
                  {g.price === 0
                    ? `Gratuit · +${fmt(g.reward ?? 50)}`
                    : `${fmt(g.price)} · +${fmt(g.reward ?? 50)}`}
                </span>
                <span
                  className="mm-qty"
                  style={{
                    background: g.is_available ? "#16a34a" : "#3f3f46",
                    borderColor: "#fff",
                    fontSize: "1.05cqw",
                  }}
                >
                  {g.is_available ? "SHOP" : "OFF"}
                </span>
              </button>
            );
          })}

          <button
            type="button"
            className={`mm-tile${selId === "new" ? " mm-tile--on" : ""}`}
            style={{
              justifyContent: "center",
              alignItems: "center",
              borderStyle: "dashed",
              borderColor: "#9aa0ff",
              minHeight: "9cqw",
            }}
            onClick={() => setSelId("new")}
          >
            <span className="mm-big" style={{ fontSize: "3.2cqw" }}>+</span>
            <span className="mm-tile-name">Nouvel objet</span>
          </button>
        </div>

        <div className="mm-btns" style={{ gap: ".6cqw" }}>
          <MeleeButton
            text="Enregistrer"
            selected={!!name.trim()}
            disabled={!name.trim()}
            height={34}
            onClick={handleSave}
          />
          {selId !== "new" && currentGage && (
            <MeleeButton
              text="Supprimer"
              height={34}
              onClick={() => onArchiveGage?.(currentGage.id)}
            />
          )}
          <MeleeButton text="Retour" height={34} onClick={onClose} />
        </div>
      </div>

      <Panel>
        <div style={{ display: "flex", alignItems: "center", gap: "1cqw" }}>
          <div style={{ width: "6.5cqw", flexShrink: 0 }}>
            <ItemImage src={imageUrl} alt={name} selected />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: ".5cqw", flex: 1 }}>
            <button
              type="button"
              className="mm-field"
              style={{ cursor: "pointer", fontSize: "1.4cqw", padding: ".6cqw .8cqw", textAlign: "center" }}
              onClick={() => setPickingSprite(true)}
            >
              Changer Sprite
            </button>
            <button
              type="button"
              className="mm-field"
              style={{
                cursor: "pointer",
                fontSize: "1.3cqw",
                padding: ".5cqw .8cqw",
                textAlign: "center",
                borderColor: isAvailable ? "#ffd000" : "#3a42e6",
                background: isAvailable ? "rgba(255, 208, 0, .22)" : "rgba(20, 24, 80, .55)",
              }}
              onClick={() => setIsAvailable((v) => !v)}
            >
              {isAvailable ? "✓ Affiché au Shop" : "Masqué du Shop"}
            </button>
          </div>
        </div>

        <Sep />

        <label className="mm-fieldwrap">
          <span className="mm-ptag">Nom de l&apos;objet</span>
          <input
            className="mm-field"
            style={{ fontSize: "1.6cqw", padding: ".6cqw .8cqw" }}
            value={name}
            placeholder="Ex: Carapace bleue"
            onChange={(e) => setName(e.target.value)}
          />
        </label>

        <label className="mm-fieldwrap">
          <span className="mm-ptag">Gage</span>
          <textarea
            className="mm-field"
            rows={2}
            style={{ fontSize: "1.45cqw", padding: ".6cqw .8cqw", resize: "none", lineHeight: 1.2 }}
            value={description}
            placeholder="Ex: Jouer tout le match sans bouclier"
            onChange={(e) => setDescription(e.target.value)}
          />
        </label>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: ".6cqw" }}>
          <label className="mm-fieldwrap">
            <span className="mm-ptag">Prix</span>
            <input
              type="number"
              min={0}
              max={100000}
              step={50}
              className="mm-field"
              style={{ fontSize: "1.5cqw", padding: ".5cqw .7cqw" }}
              value={price}
              onChange={(e) => setPrice(Number(e.target.value))}
            />
          </label>
          <label className="mm-fieldwrap">
            <span className="mm-ptag" style={{ color: "#ffe58a" }}>
              Gain
            </span>
            <input
              type="number"
              min={0}
              max={100000}
              step={50}
              className="mm-field"
              style={{ fontSize: "1.5cqw", padding: ".5cqw .7cqw" }}
              value={reward}
              onChange={(e) => setReward(Number(e.target.value))}
            />
          </label>
        </div>
      </Panel>
    </MeleeFrame>
  );
}
