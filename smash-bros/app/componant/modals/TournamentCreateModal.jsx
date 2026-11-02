import { useEffect, useState } from "react";
import MeleeFrame, { Panel, PanelRow } from "../ui/MeleeFrame";
import MeleeButton from "../ui/MeleeButton";
import { fmt } from "./ShopModal";

/**
 * Création de tournoi (admin) en 3 étapes : Informations → Règles → Publication.
 * Props : onPublish(data), onClose, open, defaults (valeurs initiales, optionnel)
 * data = { name, date, time, maxPlayers, reward, format, lives, time_limit, items }
 */
const RULES = [
  { key: "format", label: "Format", options: ["1 contre 1", "2 contre 2", "Chacun pour soi"] },
  { key: "losers_bracket", label: "Losers Bracket", options: ["Oui", "Non"] },
  { key: "lives", label: "Vies", options: [1, 2, 3, 4, 5] },
  { key: "time_limit", label: "Temps", options: ["5 min", "6 min", "7 min", "8 min", "Illimité"] },
  { key: "items", label: "Objets", options: ["Off", "On"] },
];
const PLAYERS = [8, 16, 32, 64];

export default function TournamentCreateModal({ onPublish, onOpenShopAdmin, onOpenAdminUsers, onClose, open, defaults = {} }) {
  const [step, setStep] = useState(0);
  const [todayStr, setTodayStr] = useState("");
  const [d, setD] = useState({
    name: "", date: "", time: "14:00", maxPlayers: 16, reward: 1000,
    format: "1 contre 1", losers_bracket: "Oui", lives: 3, time_limit: "7 min", items: "Off", ...defaults,
  });
  const [rule, setRule] = useState(0);
  const set = (k, v) => setD((s) => ({ ...s, [k]: v }));
  const cycle = (i, dir) => {
    const r = RULES[i], idx = r.options.indexOf(d[r.key]);
    set(r.key, r.options[(idx + dir + r.options.length) % r.options.length]);
  };

  useEffect(() => {
    const now = new Date();
    setTodayStr(
      `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`
    );
  }, []);

  useEffect(() => {
    if (!open || step !== 1) return;
    const k = (e) => {
      if (e.key === "ArrowUp") { e.preventDefault(); setRule((r) => (r - 1 + RULES.length) % RULES.length); }
      if (e.key === "ArrowDown") { e.preventDefault(); setRule((r) => (r + 1) % RULES.length); }
      if (e.key === "ArrowLeft") cycle(rule, -1);
      if (e.key === "ArrowRight") cycle(rule, 1);
    };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  });

  const isPastDate = Boolean(todayStr && d.date && d.date < todayStr);
  const infoOk = Boolean(d.name.trim() && d.date && !isPastDate);
  const dateLabel = d.date ? new Date(d.date + "T00:00").toLocaleDateString("fr-FR", { weekday: "short", day: "numeric", month: "short" }) : "";

  if (step === 0)
    return (
      <MeleeFrame open={open} onClose={onClose} title="Nouveau tournoi" sideLabel="Récap" caption="Étape 1 / 3 · Informations">
        <div className="mm-main" style={{ gap: "1.4cqw", paddingRight: "3cqw" }}>
          {(onOpenShopAdmin || onOpenAdminUsers) && (
            <div className="mm-seg">
              <button type="button" className="on">
                Nouveau Tournoi
              </button>
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
          <label className="mm-fieldwrap"><span className="mm-label">Nom du tournoi</span>
            <input className="mm-field" value={d.name} placeholder="Smash Cup #13" onChange={(e) => set("name", e.target.value)} /></label>
          <div className="mm-row2">
            <label className="mm-fieldwrap"><span className="mm-label">Date</span>
              <input className="mm-field" type="date" min={todayStr} value={d.date} onChange={(e) => set("date", e.target.value)} /></label>
            <label className="mm-fieldwrap"><span className="mm-label">Heure</span>
              <input className="mm-field" type="time" value={d.time} onChange={(e) => set("time", e.target.value)} /></label>
          </div>
          {isPastDate && (
            <span style={{ color: "#ff6b6b", fontWeight: 700, fontSize: "1.45cqw" }}>
              La date du tournoi ne peut pas être dans le passé.
            </span>
          )}
          <div className="mm-fieldwrap"><span className="mm-label">Joueurs max</span>
            <div className="mm-seg">{PLAYERS.map((n) => <button key={n} className={d.maxPlayers === n ? "on" : ""} onClick={() => set("maxPlayers", n)}>{n}</button>)}</div>
          </div>
          <div className="mm-btns">
            <MeleeButton text="Suivant" selected={!!infoOk} disabled={!infoOk} height={46} onClick={() => infoOk && setStep(1)} />
            <MeleeButton text="Retour" height={46} onClick={onClose} />
          </div>
        </div>
        <Panel>
          <PanelRow label="Format" value={d.format === "1 contre 1" ? "1v1" : d.format === "2 contre 2" ? "2v2" : "FFA"} />
          <PanelRow label="Losers" value={d.losers_bracket} />
          <PanelRow label="Joueurs" value={d.maxPlayers} />
          <PanelRow label="Vies" value={d.lives} />
          <PanelRow label="Vainqueur" value={fmt(d.reward)} gold />
        </Panel>
      </MeleeFrame>
    );

  if (step === 1)
    return (
      <MeleeFrame open={open} onClose={onClose} title="Règles" caption="Étape 2 / 3 · Règles du match">
        <div className="mm-center" style={{ gap: "2.4cqw" }}>
          <div className="mm-list" style={{ width: "64%" }}>
            {RULES.map((r, i) => (
              <div key={r.key} className={`mm-rule${i === rule ? " mm-on" : ""}`} onClick={() => setRule(i)}>
                <span>{r.label}</span>
                <span className="mm-rule-val">
                  <button className="mm-tri mm-tri--l" aria-label="Précédent" onClick={(e) => { e.stopPropagation(); cycle(i, -1); }} />
                  <span>{d[r.key]}</span>
                  <button className="mm-tri mm-tri--r" aria-label="Suivant" onClick={(e) => { e.stopPropagation(); cycle(i, 1); }} />
                </span>
              </div>
            ))}
          </div>
          <div className="mm-btns">
            <MeleeButton text="Retour" mirror height={48} onClick={() => setStep(0)} />
            <MeleeButton text="Suivant" selected height={48} onClick={() => setStep(2)} />
          </div>
        </div>
      </MeleeFrame>
    );

  return (
    <MeleeFrame open={open} onClose={onClose} title="Publier" caption="Les joueurs seront notifiés">
      <div className="mm-center">
        <span className="mm-kicker">Étape 3 / 3</span>
        <span className="mm-big">Publier {d.name} ?</span>
        <span className="mm-sub">{dateLabel} · {d.time.replace(":00", "h")} · {d.maxPlayers} joueurs · {fmt(d.reward)} Tilts au vainqueur</span>
        <div className="mm-btns" style={{ marginTop: "1cqw" }}>
          <MeleeButton text="Modifier" mirror height={56} onClick={() => setStep(0)} />
          <MeleeButton text="Publier" selected height={56} onClick={() => onPublish?.(d)} />
          <MeleeButton text="Retour" height={56} onClick={onClose} />
        </div>
      </div>
    </MeleeFrame>
  );
}
