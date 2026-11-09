import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";

/**
 * Arbre de tournoi — DA Melee (6a), version « grands tableaux ».
 * Tailles en px FIXES : plus il y a de branches, plus l'arbre grandit (au lieu de rétrécir).
 * Le zoom auto l'ajuste à la vue ; molette = zoom, glisser = déplacer.
 * Gère les tours incomplets (byes, nombre de joueurs non puissance de 2).
 */

const ON = "#9aa0ff", OFF = "#2a2e66", GOLD = "#ffd000", LINE = 3;
const CARD_W = 210, CARD_H = 64, COL_GAP = 64, SLOT = 84, HEAD = 36, CHAMP_W = 120, CHAMP_H = 96, FONT = 17;

const DEFAULT_LABELS = {
  1: ["Finale"], 2: ["Demies", "Finale"], 3: ["Quarts", "Demies", "Finale"],
  4: ["8es", "Quarts", "Demies", "Finale"], 5: ["16es", "8es", "Quarts", "Demies", "Finale"],
  6: ["32es", "16es", "8es", "Quarts", "Demies", "Finale"],
};

function winnerOf(m) {
  if (!m || m.live || !m.scores) return null;
  if (m.winner === 0 || m.winner === 1) return m.winner;
  const [a, b] = m.scores;
  return a == null || b == null || a === b ? null : a > b ? 0 : 1;
}

// centre vertical de chaque match : moyenne de ses deux matchs « parents » (2i, 2i+1) s'ils existent
function computeCenters(rounds) {
  const first = rounds[0].length;
  const centers = [rounds[0].map((_, i) => HEAD + SLOT * (i + 0.5))];
  for (let r = 1; r < rounds.length; r++) {
    const prev = centers[r - 1], n = rounds[r].length;
    centers[r] = rounds[r].map((_, i) => {
      const feeders = [prev[2 * i], prev[2 * i + 1]].filter((v) => v != null);
      if (feeders.length) return feeders.reduce((s, v) => s + v, 0) / feeders.length;
      return HEAD + (SLOT * first) * ((i + 0.5) / n); // fallback : réparti régulièrement
    });
  }
  return centers;
}

function PlayerRow({ name, score, state }) {
  const w = state === "winner", l = state === "loser";
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, paddingLeft: 12, minWidth: 0, background: "#0a0c28",
      ...(w ? { backgroundImage: "linear-gradient(90deg, rgba(255,208,0,.22), rgba(255,208,0,0) 80%)", boxShadow: `inset 5px 0 0 ${GOLD}` } : null) }}>
      <span style={{ fontStyle: "italic", fontWeight: 800, fontSize: FONT, lineHeight: 1, color: !name ? "#4b4f7a" : w ? "#fff" : l ? "#6d7096" : "#e6e7f2", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", minWidth: 0 }} title={name || ""}>
        {name || "À venir"}
      </span>
      <span style={{ flex: "none", alignSelf: "stretch", width: 34, display: "grid", placeItems: "center", fontStyle: "italic", fontWeight: 900, fontSize: FONT, background: w ? GOLD : "#14173d", color: w ? "#11132a" : !name ? "#4b4f7a" : "#8a8db0" }}>
        {score ?? "–"}
      </span>
    </div>
  );
}

function MatchCard({ match, x, y, onClick }) {
  const win = winnerOf(match);
  const st = (k) => (win === null ? "" : win === k ? "winner" : "loser");
  return (
    <div style={{ position: "absolute", left: x, top: y, width: CARD_W, height: CARD_H }}>
      <div onClick={onClick} style={{ position: "absolute", inset: 0, boxSizing: "border-box", display: "grid", gridTemplateRows: "1fr 1fr", gap: 2, background: OFF,
        border: `3px solid ${match.live ? "#ff3b3b" : match.scores ? "#4b4f9a" : OFF}`, borderRadius: 7, overflow: "hidden", cursor: onClick ? "pointer" : "default",
        boxShadow: match.live ? "0 0 16px rgba(255,59,59,.45)" : "none" }}>
        <PlayerRow name={match.players?.[0]} score={match.scores?.[0]} state={st(0)} />
        <PlayerRow name={match.players?.[1]} score={match.scores?.[1]} state={st(1)} />
      </div>
      {match.live && (
        <span style={{ position: "absolute", right: 6, top: -12, padding: "3px 8px", borderRadius: 4, background: "#ff3b3b", color: "#fff", fontWeight: 800, fontSize: 12, letterSpacing: 2, lineHeight: 1 }}>EN COURS</span>
      )}
      {match.completed && (
        <span title="Match validé par l'administrateur" style={{ position: "absolute", right: -12, top: -14, width: 28, height: 28, display: "grid", placeItems: "center", border: "2px solid #ffe58a", borderRadius: 5, background: GOLD, color: "#11132a", fontSize: 16, fontWeight: 900, lineHeight: 1, boxShadow: "0 0 10px rgba(255,208,0,.5)" }}>✓</span>
      )}
    </div>
  );
}

export default function TournamentBracket({ rounds = [], champion = null, roundLabels, championLabel = "Vainqueur", onMatchClick }) {
  const viewportRef = useRef(null);
  const dragRef = useRef(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);

  const R = rounds.length;
  const first = rounds[0]?.length ?? 0;
  const step = CARD_W + COL_GAP;
  const champX = R * step;
  const contentW = champX + CHAMP_W;
  const contentH = HEAD + SLOT * Math.max(1, first);

  // ajuste l'arbre entier dans la vue et le centre
  const fit = useCallback(() => {
    const v = viewportRef.current;
    if (!v || !R) return;
    const vw = v.clientWidth, vh = v.clientHeight;
    const z = Math.min(1.2, Math.max(0.2, Math.min(vw / contentW, vh / contentH)));
    setZoom(z);
    setPan({ x: (vw - contentW * z) / 2, y: Math.max(0, (vh - contentH * z) / 2) });
  }, [R, contentW, contentH, setPan, setZoom]);

  useLayoutEffect(() => { fit(); }, [fit]);
  useEffect(() => {
    const v = viewportRef.current;
    if (!v) return;
    const ro = new ResizeObserver(fit);
    ro.observe(v);
    return () => ro.disconnect();
  }, [fit]);

  // zoom molette centré sur le curseur (listener non passif pour pouvoir bloquer le scroll de la page)
  useEffect(() => {
    const v = viewportRef.current;
    if (!v) return;
    const onWheel = (e) => {
      e.preventDefault();
      const rect = v.getBoundingClientRect();
      const mx = e.clientX - rect.left, my = e.clientY - rect.top;
      setZoom((z) => {
        const nz = Math.min(2.5, Math.max(0.2, +(z * (e.deltaY < 0 ? 1.1 : 1 / 1.1)).toFixed(3)));
        setPan((p) => ({ x: mx - ((mx - p.x) * nz) / z, y: my - ((my - p.y) * nz) / z }));
        return nz;
      });
    };
    v.addEventListener("wheel", onWheel, { passive: false });
    return () => v.removeEventListener("wheel", onWheel);
  }, []);

  if (!R) return null;

  const labels = roundLabels || DEFAULT_LABELS[R] || rounds.map((_, i) => `Tour ${i + 1}`);
  const centers = computeCenters(rounds);

  const lines = [];
  const h = (x1, x2, y, c, k) => lines.push({ c, k, s: { left: Math.min(x1, x2) - LINE / 2, top: y - LINE / 2, width: Math.abs(x2 - x1) + LINE, height: LINE } });
  const v = (x, y1, y2, c, k) => lines.push({ c, k, s: { left: x - LINE / 2, top: Math.min(y1, y2) - LINE / 2, width: LINE, height: Math.abs(y2 - y1) + LINE } });
  rounds.forEach((ms, r) => ms.forEach((m, i) => {
    const c = winnerOf(m) === null ? OFF : ON;
    const ax = r * step + CARD_W, ay = centers[r][i];
    if (r < R - 1) {
      const by = centers[r + 1][i >> 1];
      if (by == null) return; // pas de match suivant pour ce slot
      const bx = (r + 1) * step, mx = ax + COL_GAP / 2;
      h(ax, mx, ay, c, `${r}-${i}a`); v(mx, ay, by, c, `${r}-${i}b`); h(mx, bx, by, c, `${r}-${i}c`);
    } else h(ax, champX, ay, c, `${r}-${i}f`);
  }));
  lines.sort((a, b) => (a.c === ON) - (b.c === ON));

  const finalY = centers[R - 1][0];
  const zoomBy = (f) => {
    const vEl = viewportRef.current;
    const mx = vEl ? vEl.clientWidth / 2 : 0, my = vEl ? vEl.clientHeight / 2 : 0;
    const nz = Math.min(2.5, Math.max(0.2, +(zoom * f).toFixed(3)));
    setPan((p) => ({ x: mx - ((mx - p.x) * nz) / zoom, y: my - ((my - p.y) * nz) / zoom }));
    setZoom(nz);
  };

  const onDown = (e) => {
    if (e.button !== 0 || e.target.closest("[data-match]")) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    dragRef.current = { x: e.clientX, y: e.clientY };
    setIsDragging(true);
  };
  const onMove = (e) => {
    const d = dragRef.current;
    if (!d) return;
    setPan((p) => ({ x: p.x + e.clientX - d.x, y: p.y + e.clientY - d.y }));
    dragRef.current = { x: e.clientX, y: e.clientY };
  };
  const onUp = (e) => {
    dragRef.current = null;
    setIsDragging(false);
    e.currentTarget.releasePointerCapture?.(e.pointerId);
  };

  const head = { position: "absolute", top: 0, fontWeight: 800, fontSize: 15, letterSpacing: 4, color: ON, textTransform: "uppercase", lineHeight: 1, whiteSpace: "nowrap" };
  const btn = { minWidth: 34, height: 30, padding: "0 10px", border: "2px solid #3a42e6", borderRadius: 6, background: "#0a0c28", color: "#e6e7f2", fontFamily: "inherit", fontWeight: 800, fontSize: 14, cursor: "pointer" };

  return (
    <div className="tb-shell" style={{ position: "relative", width: "100%", height: "100%", minHeight: 320, display: "flex", flexDirection: "column", gap: 8, fontFamily: "'Exo 2', sans-serif" }}>
      <div className="tb-controls" aria-label="Contrôles de l'arbre" style={{ display: "flex", alignItems: "center", gap: 6, alignSelf: "flex-end", color: "#c3c6d6", fontWeight: 800, fontSize: 14 }}>
        <button type="button" style={btn} onClick={() => zoomBy(1 / 1.2)} aria-label="Dézoomer">−</button>
        <span style={{ minWidth: 44, textAlign: "center" }}>{Math.round(zoom * 100)}%</span>
        <button type="button" style={btn} onClick={() => zoomBy(1.2)} aria-label="Zoomer">+</button>
        <button type="button" style={btn} onClick={fit}>Recentrer</button>
      </div>
      <div ref={viewportRef} className="tb-viewport" onPointerDown={onDown} onPointerMove={onMove} onPointerUp={onUp} onPointerCancel={onUp}
        title="Glissez pour déplacer l'arbre · Molette pour zoomer"
        style={{ position: "relative", flex: 1, minHeight: 0, overflow: "hidden", cursor: isDragging ? "grabbing" : "grab", touchAction: "none" }}>
        <div className="tb-canvas" style={{ position: "absolute", left: 0, top: 0, width: contentW, height: contentH, transformOrigin: "0 0", transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})` }}>
          {labels.slice(0, R).map((t, r) => <span key={`h${r}`} style={{ ...head, left: r * step, width: CARD_W }}>{t}</span>)}
          <span style={{ ...head, left: champX - 10, width: CHAMP_W + 20, textAlign: "center" }}>{championLabel}</span>
          {lines.map((l) => <div key={l.k} style={{ position: "absolute", background: l.c, ...l.s }} />)}
          {rounds.map((ms, r) => ms.map((m, i) => (
            <div key={`${r}-${i}`} data-match="">
              <MatchCard match={m} x={r * step} y={centers[r][i] - CARD_H / 2} onClick={onMatchClick ? () => onMatchClick(m, r, i) : undefined} />
            </div>
          )))}
          <div style={{ position: "absolute", left: champX, top: finalY - CHAMP_H / 2, width: CHAMP_W, height: CHAMP_H, boxSizing: "border-box", border: `3px solid ${GOLD}`, borderRadius: 8,
            background: "repeating-linear-gradient(45deg, rgba(255,208,0,.1) 0 6px, transparent 6px 12px), #0a0c28", boxShadow: "0 0 20px rgba(255,208,0,.35)",
            display: "grid", placeItems: "center", padding: "0 8px", fontStyle: "italic", fontWeight: 900, fontSize: champion ? 20 : 44, color: GOLD, textAlign: "center", overflow: "hidden", wordBreak: "break-word", lineHeight: 1.1 }}>
            {champion || "?"}
          </div>
        </div>
      </div>
    </div>
  );
}
