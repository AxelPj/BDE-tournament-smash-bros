import { useEffect, useId, useLayoutEffect, useRef } from "react";
import "../css/melee.css";

const F = "M246 155 A30 30 0 0 1 276 125 L600 125 L650 75 L1080 75 A30 30 0 0 1 1110 105 L1110 626 A30 30 0 0 1 1080 656 L276 656 A30 30 0 0 1 246 626 Z";
const TAB = "M600 125 L690 125 L740 75 L650 75 Z";
const LIGHT = "#9aa0ff", DARK = "#3a42e6";

/**
 * Cadre commun à toutes les modales.
 * Props :
 *  - title      titre en haut à gauche
 *  - sideLabel  texte vertical ; s'il est fourni, la modale a 2 colonnes (contenu + panneau)
 *  - caption    texte de la bande noire du bas
 *  - open       affiche / masque (true par défaut)
 *  - onClose    appelé sur Échap ou clic sur le fond
 *  - children   contenu. Avec sideLabel : 1er enfant = colonne gauche, 2e = panneau turquoise
 */
export default function MeleeFrame({ title, sideLabel, caption, open = true, fullScreen = false, onClose, children }) {
  const uid = "mf" + useId().replace(/[^a-zA-Z0-9]/g, "");
  const side = !!sideLabel;
  const frameRef = useRef(null);
  const titleRef = useRef(null);
  const capBoxRef = useRef(null);
  const capTextRef = useRef(null);

  useEffect(() => {
    if (!open || !onClose) return;
    const k = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [open, onClose]);

  useLayoutEffect(() => {
    if (!open) return;
    const fit = () => {
      const box = capBoxRef.current;
      const txt = capTextRef.current;
      if (box && txt) {
        const maxH = box.clientHeight || 48;
        const maxW = Math.max(40, box.clientWidth - Math.round(maxH * 0.6));
        let size = Math.min(fullScreen ? 26 : 32, Math.max(12, Math.floor(maxH * 0.54)));
        txt.style.fontSize = `${size}px`;
        while (txt.scrollWidth > maxW && size > 10) {
          size -= 1;
          txt.style.fontSize = `${size}px`;
        }
      }

      const fBox = frameRef.current;
      const tEl = titleRef.current;
      if (fBox && tEl) {
        const w = fBox.clientWidth || 800;
        const maxTW = w * 0.36;
        let tSize = Math.min(fullScreen ? 38 : 46, Math.max(14, Math.floor(w * (fullScreen ? 0.028 : 0.045))));
        tEl.style.fontSize = `${tSize}px`;
        while (tEl.scrollWidth > maxTW && tSize > 12) {
          tSize -= 1;
          tEl.style.fontSize = `${tSize}px`;
        }
      }
    };
    fit();
    if (document.fonts?.ready) {
      document.fonts.ready.then(fit);
    }
    window.addEventListener("resize", fit);
    return () => window.removeEventListener("resize", fit);
  }, [open, caption, title, fullScreen]);

  if (!open) return null;

  return (
    <div
      className={`mm-overlay${fullScreen ? " mm-overlay--fs" : ""}`}
      onClick={(e) => e.target === e.currentTarget && onClose?.()}
    >
      <div
        ref={frameRef}
        className={`mm${fullScreen ? " mm--fs" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <svg
          className="mm-svg"
          viewBox="225 60 910 620"
          preserveAspectRatio={fullScreen ? "none" : "xMidYMid meet"}
          aria-hidden="true"
        >
          <defs>
            <mask id={`${uid}in`} maskUnits="userSpaceOnUse" x="200" y="40" width="960" height="680">
              <path d={F} fill="#fff" stroke="#000" strokeWidth="18" strokeLinejoin="round" />
              <path d={`${TAB} M235 632 H398 V686 H235 Z M962 632 H1121 V686 H962 Z`} fill="#000" />
            </mask>
          </defs>
          <path d={F} fill="rgba(0,0,6,.93)" mask={`url(#${uid}in)`} />
          <g opacity=".5">
            <path d={F} fill="none" stroke={LIGHT} strokeWidth="18" strokeLinejoin="round" />
            <path d="M237 640 H392 V684 H277 A40 40 0 0 1 237 644 Z" fill={LIGHT} />
            <path d="M965 640 H1119 V644 A40 40 0 0 1 1079 684 H965 Z" fill={LIGHT} />
            <path d={TAB} fill={LIGHT} stroke={LIGHT} strokeWidth="4" strokeLinejoin="round" />
            <path d={F} fill="none" stroke={DARK} strokeWidth="14" strokeLinejoin="round" />
            <path d="M239 642 H392 V682 H277 A38 38 0 0 1 239 644 Z" fill={DARK} />
            <path d="M965 642 H1117 V644 A38 38 0 0 1 1079 682 H965 Z" fill={DARK} />
            <path d={TAB} fill={DARK} />
            <path d="M623 125 L673 75 M646 125 L696 75 M669 125 L719 75" stroke={LIGHT} strokeWidth="2.5" />
          </g>
          {side && (
            <g className="mm-svg-side">
              <path d="M800 178 L1088 162 L1104 176 L1104 602 L800 602 Z" fill="none" stroke="#7f8296" strokeWidth="3" strokeLinejoin="round" />
              <path d="M800 252 L826 252 L842 268 L842 538 L826 554 L800 554" fill="none" stroke="#7f8296" strokeWidth="3" strokeLinejoin="round" />
            </g>
          )}
        </svg>
        <span ref={titleRef} className="mm-title">{title}</span>
        {side && <span className="mm-sidelabel">{sideLabel}</span>}
        <div className={`mm-body${side ? " mm-body--side" : ""}`}>{children}</div>
        {caption && (
          <div ref={capBoxRef} className="mm-caption">
            <span ref={capTextRef} className="mm-caption-text">{caption}</span>
          </div>
        )}
      </div>
    </div>
  );
}

/* Petits blocs réutilisables */
export const Panel = ({ children, center }) => <div className={`mm-panel${center ? " mm-panel--center" : ""}`}>{children}</div>;
export const PanelRow = ({ label, value, gold }) => (
  <div className="mm-prow"><span>{label}</span><span className={gold ? "mm-gold" : ""}>{value}</span></div>
);
export const Sep = () => <div className="mm-sep" />;
export const ItemImage = ({ src, alt, selected, round }) => (
  <div className={`mm-ph${selected ? " mm-ph--on" : ""}${round ? " mm-ph--round" : ""}`}>
    {src ? <img src={src} alt={alt || ""} /> : <span>objet</span>}
  </div>
);
