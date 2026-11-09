const ON = "#9aa0ff";
const OFF = "#2a2e66";
const GOLD = "#ffd000";
const LINE = 0.3;

const DEFAULT_LABELS = {
  1: ["Finale"],
  2: ["Demies", "Finale"],
  3: ["Quarts", "Demies", "Finale"],
  4: ["8es", "Quarts", "Demies", "Finale"],
  5: ["16es", "8es", "Quarts", "Demies", "Finale"],
};

function winnerOf(match) {
  if (!match || match.live || !match.scores) return null;
  if (match.winner === 0 || match.winner === 1) return match.winner;
  const [a, b] = match.scores;
  return a == null || b == null || a === b ? null : a > b ? 0 : 1;
}

export default function TournamentBracket({
  rounds = [],
  champion = null,
  roundLabels,
  championLabel = "Vainqueur",
  onMatchClick,
}) {
  const viewportRef = useRef(null);
  const canvasRef = useRef(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const dragRef = useRef(null);
  const roundCount = rounds.length;
  const firstRoundLength = rounds[0]?.length ?? 0;

  const scale = 100 / 88;
  const unit = (value) => `${+(value * scale).toFixed(3)}cqw`;
  const labels =
    roundLabels || DEFAULT_LABELS[roundCount] || rounds.map((_, index) => `Tour ${index + 1}`);
  const step = 78 / roundCount;
  const width = step * 0.73;
  const fontSize = Math.min(1.65, (1.65 * width) / 19);
  const top = 3.6;
  const firstMatchCount = rounds[0].length;
  const slot = firstMatchCount <= 4 ? 42.4 / firstMatchCount : 7;
  const height = Math.min(7.2, slot * 0.68);
  const bracketHeight = top + slot * firstMatchCount;
  const championWidth = 10;
  const championX = 78;

  useEffect(() => {
    setZoom(1);
    const frame = requestAnimationFrame(() => {
      const viewport = viewportRef.current;
      const canvas = canvasRef.current;
      const overflow = canvas && viewport ? canvas.offsetHeight - viewport.clientHeight : 0;
      setPan({ x: 0, y: overflow > 0 ? -overflow / 2 : 0 });
    });
    return () => cancelAnimationFrame(frame);
  }, [roundCount, firstRoundLength]);

  if (!roundCount) return null;

  const changeZoom = (delta) => {
    setZoom((value) => Math.min(2.5, Math.max(0.45, +(value + delta).toFixed(2))));
  };

  const recenter = () => {
    setZoom(1);
    const viewport = viewportRef.current;
    const canvas = canvasRef.current;
    const overflow = canvas && viewport ? canvas.offsetHeight - viewport.clientHeight : 0;
    setPan({ x: 0, y: overflow > 0 ? -overflow / 2 : 0 });
  };

  const handleWheel = (event) => {
    event.preventDefault();
    changeZoom(event.deltaY < 0 ? 0.1 : -0.1);
  };

  const handlePointerDown = (event) => {
    if (event.button !== 0) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = { pointerId: event.pointerId, x: event.clientX, y: event.clientY };
  };

  const handlePointerMove = (event) => {
    if (!dragRef.current) return;
    const previous = dragRef.current;
    setPan((value) => ({
      x: value.x + event.clientX - previous.x,
      y: value.y + event.clientY - previous.y,
    }));
    dragRef.current = { ...previous, x: event.clientX, y: event.clientY };
  };

  const handlePointerUp = (event) => {
    if (!dragRef.current) return;
    event.currentTarget.releasePointerCapture?.(event.pointerId);
    dragRef.current = null;
  };

  const centers = [rounds[0].map((_, index) => top + slot * (index + 0.5))];
  for (let round = 1; round < roundCount; round += 1) {
    centers[round] = rounds[round].map(
      (_, index) => (centers[round - 1][2 * index] + centers[round - 1][2 * index + 1]) / 2
    );
  }

  const lines = [];
  const horizontal = (x1, x2, y, color, key) =>
    lines.push({
      color,
      key,
      style: {
        left: unit(Math.min(x1, x2) - LINE / 2),
        top: unit(y - LINE / 2),
        width: unit(Math.abs(x2 - x1) + LINE),
        height: unit(LINE),
      },
    });
  const vertical = (x, y1, y2, color, key) =>
    lines.push({
      color,
      key,
      style: {
        left: unit(x - LINE / 2),
        top: unit(Math.min(y1, y2) - LINE / 2),
        width: unit(LINE),
        height: unit(Math.abs(y2 - y1) + LINE),
      },
    });

  rounds.forEach((matches, round) =>
    matches.forEach((match, index) => {
      const color = winnerOf(match) === null ? OFF : ON;
      const startX = round * step + width;
      const startY = centers[round][index];
      if (round < roundCount - 1) {
        const endX = (round + 1) * step;
        const endY = centers[round + 1][Math.floor(index / 2)];
        const middleX = (startX + endX) / 2;
        horizontal(startX, middleX, startY, color, `${round}-${index}-a`);
        vertical(middleX, startY, endY, color, `${round}-${index}-b`);
        horizontal(middleX, endX, endY, color, `${round}-${index}-c`);
      } else {
        horizontal(startX, championX, startY, color, `${round}-${index}-final`);
      }
    })
  );

  const renderHeader = ({ x, width: headerWidth, text, align = "left" }) => (
    <span
      style={{
        position: "absolute",
        left: unit(x),
        top: 0,
        width: unit(headerWidth),
        textAlign: align,
        fontWeight: 800,
        fontSize: unit(1.25),
        letterSpacing: unit(0.35),
        color: ON,
        textTransform: "uppercase",
        lineHeight: 1,
        whiteSpace: "nowrap",
      }}
    >
      {text}
    </span>
  );

  const PlayerRow = ({ name, score, state }) => {
    const isWinner = state === "winner";
    const isLoser = state === "loser";
    return (
      <div style={{ display: "grid", background: "#0a0c28" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: unit(0.6),
            paddingLeft: unit(0.9),
            minWidth: 0,
            ...(isWinner
              ? {
                  background: "linear-gradient(90deg, rgba(255,208,0,.22), rgba(255,208,0,0) 80%)",
                  boxShadow: `inset ${unit(0.35)} 0 0 ${GOLD}`,
                }
              : {}),
          }}
        >
          <span
            style={{
              fontStyle: "italic",
              fontWeight: 800,
              fontSize: unit(fontSize),
              lineHeight: 1,
              color: !name ? "#4b4f7a" : isWinner ? "#fff" : isLoser ? "#6d7096" : "#e6e7f2",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
              minWidth: 0,
            }}
          >
            {name || "À venir"}
          </span>
          <span
            style={{
              flex: "none",
              alignSelf: "stretch",
              width: unit(fontSize * 1.9),
              display: "grid",
              placeItems: "center",
              fontStyle: "italic",
              fontWeight: 900,
              fontSize: unit(fontSize),
              background: isWinner ? GOLD : "#14173d",
              color: isWinner ? "#11132a" : !name ? "#4b4f7a" : "#8a8db0",
            }}
          >
            {score ?? "–"}
          </span>
        </div>
      </div>
    );
  };

  const MatchCard = ({ match, round, index }) => {
    const winner = winnerOf(match);
    const completed = Boolean(match.completed);
    const state = (playerIndex) =>
      winner === null ? "" : winner === playerIndex ? "winner" : "loser";
    const x = round * step;
    const y = centers[round][index] - height / 2;

    return (
      <div
        onClick={onMatchClick ? () => onMatchClick(match, round, index) : undefined}
        style={{
          position: "absolute",
          left: unit(x),
          top: unit(y),
          width: unit(width),
          height: unit(height),
          boxSizing: "border-box",
          display: "grid",
          gridTemplateRows: "1fr 1fr",
          gap: unit(0.15),
          background: OFF,
          border: `${unit(0.2)} solid ${match.live ? "#ff3b3b" : match.scores ? "#4b4f9a" : OFF}`,
          borderRadius: unit(0.5),
          overflow: "hidden",
          cursor: onMatchClick ? "pointer" : "default",
          boxShadow: match.live ? `0 0 ${unit(1.2)} rgba(255,59,59,.45)` : "none",
        }}
      >
        {completed && (
          <span
            title="Match validé par l'administrateur"
            style={{
              position: "absolute",
              zIndex: 2,
              top: unit(-1.35),
              right: unit(-1.05),
              width: unit(2.2),
              height: unit(2.2),
              display: "grid",
              placeItems: "center",
              border: `${unit(0.18)} solid #ffe58a`,
              borderRadius: unit(0.35),
              background: GOLD,
              color: "#11132a",
              fontSize: unit(1.25),
              fontWeight: 900,
              lineHeight: 1,
              boxShadow: `0 0 ${unit(0.8)} rgba(255,208,0,.5)`,
            }}
          >
            ✓
          </span>
        )}
        <PlayerRow name={match.players?.[0]} score={match.scores?.[0]} state={state(0)} />
        <PlayerRow name={match.players?.[1]} score={match.scores?.[1]} state={state(1)} />
      </div>
    );
  };

  const finalCenter = centers[roundCount - 1][0];
  return (
    <div className="tb-shell">
      <div className="tb-controls" aria-label="Contrôles de l'arbre">
        <button type="button" onClick={() => changeZoom(-0.1)} aria-label="Dézoomer">−</button>
        <span>{Math.round(zoom * 100)}%</span>
        <button type="button" onClick={() => changeZoom(0.1)} aria-label="Zoomer">+</button>
        <button type="button" onClick={recenter} aria-label="Recentrer">
          Recentrer
        </button>
      </div>
      <div
        ref={viewportRef}
        className="tb-viewport"
        onWheel={handleWheel}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        title="Glissez pour déplacer l'arbre · Molette pour zoomer"
      >
        <div
          className="tb-canvas"
          ref={canvasRef}
          style={{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
          }}
        >
        <div style={{ width: "100%", containerType: "inline-size", fontFamily: "'Exo 2', sans-serif" }}>
          <div style={{ position: "relative", width: "100%", height: unit(bracketHeight) }}>
        {labels.slice(0, roundCount).map((text, round) => (
          <span key={`header-${round}`}>
            {renderHeader({ x: round * step, width, text })}
          </span>
        ))}
        {renderHeader({
          x: championX - 2,
          width: championWidth + 4,
          text: championLabel,
          align: "center",
        })}
        {lines
          .sort((a, b) => (a.color === ON) - (b.color === ON))
          .map((line) => (
            <div key={line.key} style={{ position: "absolute", background: line.color, ...line.style }} />
          ))}
        {rounds.map((matches, round) =>
          matches.map((match, index) => (
            <MatchCard key={`${round}-${index}`} match={match} round={round} index={index} />
          ))
        )}
        <div
          style={{
            position: "absolute",
            left: unit(championX),
            top: unit(finalCenter - 5),
            width: unit(championWidth),
            height: unit(10),
            boxSizing: "border-box",
            border: `${unit(0.3)} solid ${GOLD}`,
            borderRadius: unit(0.6),
            background: `repeating-linear-gradient(45deg, rgba(255,208,0,.1) 0 ${unit(0.5)}, transparent ${unit(0.5)} ${unit(1)}), #0a0c28`,
            boxShadow: `0 0 ${unit(1.6)} rgba(255,208,0,.35)`,
            display: "grid",
            placeItems: "center",
            padding: `0 ${unit(0.6)}`,
            fontStyle: "italic",
            fontWeight: 900,
            fontSize: unit(champion ? 1.7 : 4),
            color: GOLD,
            textAlign: "center",
            overflow: "hidden",
            wordBreak: "break-word",
            lineHeight: 1.1,
          }}
        >
          {champion || "?"}
        </div>
          </div>
        </div>
        </div>
      </div>
    </div>
  );
}
import { useEffect, useRef, useState } from "react";
