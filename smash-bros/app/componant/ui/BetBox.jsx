import { useEffect, useRef, useState } from "react";
import MeleeButton from "./MeleeButton";
import { apiJson, fmt } from "../../lib/utils";

/**
 * Cotes d'un match (tournoi ou duel) + mes mises dessus, rafraîchies toutes les 5s.
 * marketUrl : URL GET des cotes (null = pas de chargement).
 * isMine(bet) : dit si un pari de /api/bets/mine porte sur ce match.
 * Renvoie { market, mine: { [playerId]: montant }, refresh }.
 */
export function useBetMarket(marketUrl, isMine, currentUserId) {
  const [info, setInfo] = useState(null); // { url, market, mine }
  const [refreshKey, setRefreshKey] = useState(0);
  const isMineRef = useRef(isMine);
  useEffect(() => {
    isMineRef.current = isMine;
  });

  useEffect(() => {
    if (!marketUrl) return;
    let cancelled = false;
    const load = async () => {
      if (document.visibilityState !== "visible") return;
      const [market, myBets] = await Promise.all([
        apiJson(marketUrl).catch(() => null),
        currentUserId ? apiJson("/api/bets/mine").catch(() => null) : Promise.resolve(null),
      ]);
      if (cancelled) return;
      const mine = {};
      for (const b of myBets || []) {
        if (b.status !== "refunded" && isMineRef.current(b)) {
          mine[b.picked_player_id] = (mine[b.picked_player_id] || 0) + b.amount;
        }
      }
      setInfo({ url: marketUrl, market, mine });
    };
    load();
    const id = setInterval(load, 5000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [marketUrl, currentUserId, refreshKey]);

  const current = info?.url === marketUrl ? info : null;
  return {
    market: current?.market ?? null,
    mine: current?.mine ?? null,
    refresh: () => setRefreshKey((n) => n + 1),
  };
}

/** « Cote x1.5 · Ma mise 20 », affiché sous le nom d'un joueur. */
/** @param {Record<string, any>} props */
export function BetTag({ market, mine, playerId }) {
  if (!market || !playerId) return null;
  const odds = market.players?.find((p) => p.user_id === playerId)?.odds;
  const myStake = mine?.[playerId] || 0;
  return (
    <span
      style={{
        display: "block",
        fontSize: "clamp(10px, calc(.9 * var(--u)), 14px)",
        fontWeight: 800,
        fontStyle: "normal",
        color: "#ffe58a",
      }}
    >
      {odds ? `Cote x${odds}` : "Cote —"}
      {myStake > 0 && <span style={{ color: "#4ade80" }}> · Ma mise {fmt(myStake)}</span>}
    </span>
  );
}

/**
 * Bouton « Parier » + formulaire de pari sur un match (tournoi ou duel).
 * players : [id joueur 1, id joueur 2]
 * onPlaceBet(pickedPlayerId, amount) -> Promise<{ ok, error? }>
 */
/** @param {Record<string, any>} props */
export default function BetBox({ players, getPlayerName, balance, market, onPlaceBet, onBetPlaced }) {
  const [openForm, setOpenForm] = useState(false);
  const [pick, setPick] = useState(null);
  const [amount, setAmount] = useState(10);
  const [msg, setMsg] = useState(null); // { ok: bool, text: string }

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
    const res = await onPlaceBet?.(pick, amount);
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
    fontSize: "clamp(11px, calc(1.05 * var(--u)), 16px)",
    padding: "calc(.35 * var(--u)) calc(.5 * var(--u))",
    textAlign: "center",
    borderColor: selected ? "#ffd000" : "#3a42e6",
    background: selected ? "rgba(255, 208, 0, .25)" : "rgba(20, 24, 80, .6)",
    color: "#fff",
    display: "flex",
    flexDirection: "column",
    gap: "calc(.15 * var(--u))",
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "calc(.5 * var(--u))" }}>
      <span className="mm-ptag" style={{ color: "#ffd000" }}>
        Parier · {market ? fmt(market.total_bettors) : "…"} parieur
        {market?.total_bettors > 1 ? "s" : ""}
      </span>
      <div style={{ display: "flex", gap: "calc(.4 * var(--u))" }}>
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
              <span style={{ fontSize: "clamp(10px, calc(.9 * var(--u)), 14px)", opacity: 0.85 }}>
                {o?.odds
                  ? `Cote x${o.odds} · ${o.bettors} parieur${o.bettors > 1 ? "s" : ""}`
                  : "Aucun parieur"}
              </span>
            </button>
          );
        })}
      </div>
      <div className="mm-prow" style={{ alignItems: "center" }}>
        <span style={{ fontSize: "clamp(12px, calc(1.15 * var(--u)), 18px)" }}>
          Mise (solde {fmt(balance)})
        </span>
        <input
          type="number"
          min={1}
          max={balance ?? 0}
          className="mm-field"
          style={{
            width: "clamp(64px, calc(5.5 * var(--u)), 90px)",
            padding: "clamp(4px, calc(.35 * var(--u)), 8px) clamp(6px, calc(.5 * var(--u)), 10px)",
            fontSize: "clamp(13px, calc(1.25 * var(--u)), 20px)",
          }}
          value={amount}
          onChange={(e) => setAmount(Math.floor(Number(e.target.value)))}
        />
      </div>
      {msg && (
        <span
          style={{
            fontSize: "clamp(11px, calc(1 * var(--u)), 15px)",
            fontWeight: 800,
            color: msg.ok ? "#4ade80" : "#f87171",
          }}
        >
          {msg.text}
        </span>
      )}
      <div style={{ display: "flex", gap: "calc(.4 * var(--u))" }}>
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
