import { useId, useLayoutEffect, useRef, useState } from "react";
import "../css/MeleeButton.css";

/**
 * Bouton façon menu Super Smash Bros. Melee.
 *
 * Props :
 *  - text      (string)  texte affiché dans le bouton            ex: "Connexion"
 *  - href      (string)  si fourni, le bouton est un lien <a>
 *  - onClick   (func)    action au clic
 *  - selected  (bool)    reste en jaune (état sélectionné) en permanence
 *  - flip      (bool)    inverse la forme horizontalement (pointe à droite, cible à gauche)
 *  - height    (number)  hauteur en px (56 par défaut) — tout le dessin suit
 *  - className, style, ...rest : passés à l'élément
 */
let __actx;
function blip(f1, f2, d, vol = 0.05) {
  if (typeof window === "undefined") return;
  try {
    __actx = __actx || new (window.AudioContext || window.webkitAudioContext)();
    const t = __actx.currentTime, o = __actx.createOscillator(), g = __actx.createGain();
    o.type = "square";
    o.frequency.setValueAtTime(f1, t);
    o.frequency.exponentialRampToValueAtTime(f2, t + d);
    g.gain.setValueAtTime(vol, t);
    g.gain.exponentialRampToValueAtTime(0.0001, t + d);
    o.connect(g).connect(__actx.destination);
    o.start(t); o.stop(t + d);
  } catch (e) {}
}

export default function MeleeButton({
  text,
  href,
  onClick,
  onMouseEnter,
  selected = false,
  disabled = false,
  flip = false,
  mirror = false,
  sound = true,
  height,
  className = "",
  style,
  ...rest
}) {
  const ref = useRef(null);
  const [size, setSize] = useState({ w: 0, h: 0 });
  const id = "mb" + useId().replace(/[^a-zA-Z0-9]/g, "");
  const isFlipped = flip || mirror;

  // le dessin se recalcule à la taille réelle du bouton (texte plus long = bouton plus long)
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const measure = () => setSize({ w: el.offsetWidth, h: el.offsetHeight });
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const Tag = href ? "a" : "button";
  const tagProps = href ? { href } : { type: "button", disabled };

  return (
    <Tag
      ref={ref}
      className={`mbtn${selected && !disabled ? " mbtn--hot" : ""}${disabled ? " mbtn--disabled" : ""}${isFlipped ? " mbtn--flip" : ""} ${className}`}
      style={{
        ...(height
          ? {
              "--h-base": `${height}px`,
              "--h-cqw": `${(height * 0.1).toFixed(2)}cqw`,
              "--h": `${height}px`,
            }
          : {}),
        ...style,
      }}
      onClick={(e) => {
        if (disabled) return;
        if (sound) blip(520, 1500, 0.14, 0.06);
        onClick?.(e);
      }}
      onMouseEnter={(e) => {
        if (disabled) return;
        if (sound && __actx) blip(1100, 1300, 0.04, 0.03);
        onMouseEnter?.(e);
      }}
      {...tagProps}
      {...rest}
    >
      {size.w > 0 && <MeleeShape id={id} W={size.w} H={size.h} />}
      <span className="mbtn__label">{text}</span>
    </Tag>
  );
}

function MeleeShape({ id, W, H }) {
  const t = H * 0.12, cy = H / 2, R = H / 2, cx = W - R, tip = H * 0.32;
  const bw = H * 0.1, xs = cx - bw, rD = H * 0.3; // barre du P + creux en D
  const rb = H * 0.12, by = cy, sw = H * 0.05;     // petite boule du P + trait
  const outer = `M0 ${cy} L${tip} 0 L${cx} 0 A${R} ${R} 0 0 1 ${cx} ${H} L${tip} ${H} Z`;
  const inner = `M${t * 1.3} ${cy} L${tip + t * 0.6} ${t} L${xs} ${t} L${xs} ${H - t} L${tip + t * 0.6} ${H - t} Z`;
  const dcut = `M${cx} ${cy - rD} A${rD} ${rD} 0 0 1 ${cx} ${cy + rD} Z`;
  const bowl = `M${cx} ${by - rb} A${rb} ${rb} 0 0 1 ${cx} ${by + rb} Z`;
  const pHalf = `M${cx} ${cy - H * 0.3} A${H * 0.3} ${H * 0.3} 0 0 1 ${cx} ${cy + H * 0.3} L${cx} ${cy + H * 0.15} A${H * 0.15} ${H * 0.15} 0 0 0 ${cx} ${cy - H * 0.15} Z`;
  const u = (s) => `url(#${id}${s})`;

  return (
    <svg aria-hidden="true" width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
      <defs>
        <mask id={`${id}m`} maskUnits="userSpaceOnUse" x={-20} y={-20} width={W + 40} height={H + 40}>
          <rect x={-20} y={-20} width={W + 40} height={H + 40} fill="#fff" />
          <path d={inner} fill="#000" />
          <path d={dcut} fill="#000" />
          <path d={bowl} fill="#fff" />
          <rect x={cx} y={by + rb - 1} width={sw} height={H - by - rb + 3} fill="#000" />
        </mask>
        <linearGradient id={`${id}g`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#e2b04c" />
          <stop offset=".5" stopColor="#d09a36" />
          <stop offset="1" stopColor="#b27e22" />
        </linearGradient>
        <linearGradient id={`${id}w`} x1="0" x2="1">
          <stop offset="0" stopColor="#fff" />
          <stop offset=".6" stopColor="#fffbe0" stopOpacity=".7" />
          <stop offset="1" stopColor="#fff" stopOpacity="0" />
        </linearGradient>
        <filter id={`${id}b`} x="-10%" y="-40%" width="120%" height="180%">
          <feGaussianBlur stdDeviation={H * 0.05} />
        </filter>
        <filter id={`${id}s`} x="-5%" y="-20%" width="110%" height="140%">
          <feGaussianBlur stdDeviation={Math.max(0.9, H * 0.022)} />
        </filter>
      </defs>

      {/* repos : bande dorée, intérieur transparent (flou seulement sur le bord extérieur) */}
      <g className="mb-idle">
        <g mask={u("m")}>
          <path d={outer} fill="#d9a23c" opacity=".3" filter={u("b")} />
          <path d={outer} fill={u("g")} opacity=".85" filter={u("s")} />
        </g>
      </g>

      {/* sélectionné : tout jaune */}
      <g className="mb-hot">
        <circle className="mb-ripple" cx={cx} cy={cy} r={H * 0.75} fill="none" stroke="#b9bcff" strokeOpacity=".55" strokeWidth={H * 0.04} />
        <circle className="mb-ripple r2" cx={cx} cy={cy} r={H * 0.75} fill="none" stroke="#b9bcff" strokeOpacity=".55" strokeWidth={H * 0.04} />
        <path d={outer} fill="#ffd000" opacity=".6" filter={u("b")} />
        <path d={outer} fill="#ffd000" filter={u("s")} />
        <path className="mb-flash" d={outer} fill={u("w")} />
      </g>

      {/* trait du "P" : toujours là ; au survol il passe derrière la cible */}
      <line x1={cx + sw / 2} y1={by + rb} x2={cx + sw / 2} y2={H + H * 0.07} stroke="#0a0a18" strokeOpacity=".9" strokeWidth={sw} />

      {/* cible qui apparaît par-dessus au survol */}
      <g className="mb-hot mb-target">
        <circle cx={cx} cy={cy} r={H * 0.62} fill="#e6ea8c" opacity=".55" filter={u("b")} />
        <circle cx={cx} cy={cy} r={H * 0.58} fill="#e6ea8c" fillOpacity=".6" />
        <circle cx={cx} cy={cy} r={H * 0.4} fill="none" stroke="#f5d200" strokeWidth={H * 0.07} />
        <path d={pHalf} fill="#5d6c64" />
        <circle cx={cx} cy={cy} r={H * 0.08} fill="#111" />
      </g>
    </svg>
  );
}
