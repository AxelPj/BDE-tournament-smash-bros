import { memo, useEffect, useLayoutEffect, useRef, useState } from "react";
import MeleeButton from "../ui/MeleeButton";
import "../css/CharacterSelectScreen.css";

/**
 * Écran plein écran de choix du personnage (= photo de profil) parmi les 84 combattants.
 * - Main Master Hand à la place du curseur.
 * - On attrape la pièce, on la porte sur un personnage, on lâche → sélection.
 * - Un clic ailleurs : la main fait le pistolet et tire une boule de feu.
 */
// Scène de référence : paysage 1280×720, ou portrait 720×1280 sur téléphone vertical
const LANDSCAPE = [1280, 720], PORTRAIT = [720, 1280];

const CharacterTile = memo(function CharacterTile({ character, index, selected }) {
  return (
    <div
      data-char={index}
      className={`cs-tile${selected ? " on" : ""}`}
      style={
        character.color
          ? {
              background: `radial-gradient(circle at 50% 40%, ${character.color}, color-mix(in srgb, ${character.color} 45%, #12143a))`,
            }
          : undefined
      }
    >
      {(character.tile || character.image) && (
        <img
          src={character.tile || character.image}
          alt=""
          draggable="false"
          width={84}
          height={48}
          decoding="async"
        />
      )}
      <span className="cs-name">{character.name}</span>
    </div>
  );
});

/** @param {Record<string, any>} props */
export default function CharacterSelectScreen({
  characters = [],
  selectedId,
  login = "",
  onSelect,
  onClose,
  open = true,
  assetsPath = "/smash",
}) {
  const N = characters.length;
  const [sel, setSel] = useState(0);
  const selRef = useRef(0);
  useLayoutEffect(() => {
    selRef.current = sel;
  }, [sel]);
  const [tok, setTok] = useState(null);
  const [drag, setDrag] = useState(false);
  const [gun, setGun] = useState(false);
  const [scale, setScale] = useState(1);
  const [portrait, setPortrait] = useState(false);
  const [W, H] = portrait ? PORTRAIT : LANDSCAPE;
  const stageRef = useRef(null),
    layerRef = useRef(null),
    handRef = useRef(null),
    coinRef = useRef(null),
    nameRef = useRef(null),
    loginRef = useRef(null);
  const st = useRef({ drag: false, gun: false, ptr: null, gunT: null, moveRaf: 0, pendingMove: null });
  useLayoutEffect(() => {
    st.current.drag = drag;
    st.current.gun = gun;
  }, [drag, gun]);
  const A = (f) => `${assetsPath}/${f}`;

  useEffect(() => {
    if (!open || !characters.length) return;
    const idx = characters.findIndex(
      (c) => c.id === selectedId || c.image === selectedId
    );
    setSel(idx >= 0 ? idx : 0);
  }, [open, selectedId, characters]);

  // Précharge les grands portraits en tâche de fond (~30 Ko chacun en WebP) :
  // le survol d'un personnage affiche alors son portrait instantanément.
  useEffect(() => {
    if (!open || !characters.length) return;
    const idle = window.requestIdleCallback || ((cb) => setTimeout(cb, 300));
    const cancel = window.cancelIdleCallback || clearTimeout;
    const id = idle(() => {
      for (const ch of characters) {
        if (!ch.portrait) continue;
        const img = new Image();
        img.decoding = "async";
        img.src = ch.portrait;
      }
    });
    return () => cancel(id);
  }, [open, characters]);

  // mise à l'échelle 1280×720 → fenêtre (ordinateur + téléphone)
  useEffect(() => {
    const fit = () => {
      const vw = window.visualViewport?.width || window.innerWidth;
      const vh = window.visualViewport?.height || window.innerHeight;
      const isPortrait = vh > vw;
      const [w, h] = isPortrait ? PORTRAIT : LANDSCAPE;
      setPortrait(isPortrait);
      setScale(Math.min((vw - 12) / w, (vh - 12) / h));
    };
    fit();
    window.addEventListener("resize", fit);
    window.visualViewport?.addEventListener("resize", fit);
    return () => {
      window.removeEventListener("resize", fit);
      window.visualViewport?.removeEventListener("resize", fit);
    };
  }, []);

  useEffect(() => {
    if (!open) return;
    const k = (e) => e.key === "Escape" && onClose?.();
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [open, onClose]);

  const c = characters[sel] || {};

  // Ajustement automatique de la taille du nom (84px -> min 36px) et du login (30px -> min 14px)
  useLayoutEffect(() => {
    if (!open) return;
    const fitText = () => {
      const el = nameRef.current;
      if (el && el.parentElement) {
        let size = 84;
        el.style.fontSize = `${size}px`;
        const maxW = Math.min(
          el.clientWidth || Infinity,
          el.parentElement.clientWidth * 0.55
        );
        while (el.scrollWidth > maxW && size > 36) {
          size -= 2;
          el.style.fontSize = `${size}px`;
        }
      }

      const lEl = loginRef.current;
      const p1El = nameRef.current?.parentElement;
      if (lEl && p1El) {
        let lSize = 30;
        lEl.style.fontSize = `${lSize}px`;
        const maxLW = p1El.clientWidth * 0.55 - 112;
        while (lEl.scrollWidth > maxLW && lSize > 14) {
          lSize -= 2;
          lEl.style.fontSize = `${lSize}px`;
        }
      }
    };
    fitText();
    if (document.fonts?.ready) {
      document.fonts.ready.then(fitText);
    }
  }, [open, sel, c.name, login, scale]);

  const geo = () => {
    const l = layerRef.current;
    if (!l) return null;
    const sr = l.getBoundingClientRect();
    return { l, sr, k: sr.width / (l.offsetWidth || 1) };
  };
  const snap = (i) => {
    const g = geo();
    if (!g || !stageRef.current) return;
    const el = stageRef.current.querySelector(`[data-char="${i}"]`);
    if (!el) return;
    const tr = el.getBoundingClientRect();
    setTok({ x: (tr.left - g.sr.left) / g.k + 24, y: (tr.top - g.sr.top) / g.k - 4 });
  };
  useEffect(() => {
    if (open) {
      // selRef : la sélection à jour (le perso actuel est choisi juste après l'ouverture)
      const t = setTimeout(() => snap(selRef.current), 50);
      return () => clearTimeout(t);
    }
  }, [open, scale, portrait]); // eslint-disable-line

  useEffect(
    () => () => {
      if (st.current.moveRaf) cancelAnimationFrame(st.current.moveRaf);
      clearTimeout(st.current.gunT);
    },
    []
  );

  const hit = (cx, cy) => {
    const el = document
      .elementsFromPoint(cx, cy)
      .find((n) => n.dataset?.char != null && stageRef.current?.contains(n));
    return el ? Number(el.dataset.char) : null;
  };

  const placeHand = (e) => {
    const g = geo(), el = handRef.current;
    if (!g || !el) return;
    const x = (e.clientX - g.sr.left) / g.k, y = (e.clientY - g.sr.top) / g.k;
    st.current.ptr = { x, y };
    const [dx, dy] = st.current.drag ? [-6, -20] : st.current.gun ? [-62, -20] : [-54, -4];
    el.style.transform = `translate(${x + dx}px,${y + dy}px)`;
    el.style.opacity = "1";
  };

  const tokDown = (e) => {
    e.preventDefault();
    e.stopPropagation();
    const g = geo();
    if (!g) return;
    const off = 18;
    const initial = { x: (e.clientX - g.sr.left) / g.k - off, y: (e.clientY - g.sr.top) / g.k - off };
    setTok(initial);
    st.current.drag = true;
    setDrag(true);
    placeHand(e);
    const move = (ev) => {
      st.current.pendingMove = ev;
      if (st.current.moveRaf) return;
      st.current.moveRaf = requestAnimationFrame(() => {
        st.current.moveRaf = 0;
        const current = st.current.pendingMove;
        if (!current) return;
        const x = Math.max(-10, Math.min(W - 30, (current.clientX - g.sr.left) / g.k - off));
        const y = Math.max(-10, Math.min(H - 30, (current.clientY - g.sr.top) / g.k - off));
        if (coinRef.current) {
          coinRef.current.style.left = `${x}px`;
          coinRef.current.style.top = `${y}px`;
        }
        const i = hit(current.clientX, current.clientY);
        if (i != null && i < N && i !== selRef.current) setSel(i);
      });
    };
    const up = (ev) => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      if (st.current.moveRaf) {
        cancelAnimationFrame(st.current.moveRaf);
        st.current.moveRaf = 0;
      }
      const i = hit(ev.clientX, ev.clientY);
      st.current.drag = false;
      setDrag(false);
      if (i === N) {
        const k = Math.floor(Math.random() * N);
        setSel(k);
        requestAnimationFrame(() => snap(k));
      } else if (i != null) {
        // Relâché sur une vignette (même sans glisser) : elle devient la sélection
        setSel(i);
        snap(i);
      }
      const current = st.current.pendingMove;
      if (current) {
        setTok({
          x: Math.max(-10, Math.min(W - 30, (current.clientX - g.sr.left) / g.k - off)),
          y: Math.max(-10, Math.min(H - 30, (current.clientY - g.sr.top) / g.k - off)),
        });
      }
      st.current.pendingMove = null;
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  };

  // Rayon de prise du jeton : 64px dans la scène, mais jamais moins de 44px réels à
  // l'écran (la scène est réduite sur petit écran, la zone resterait minuscule).
  const nearCoin = (e) => {
    const g = geo();
    if (!g || !tok) return false;
    const x = (e.clientX - g.sr.left) / g.k, y = (e.clientY - g.sr.top) / g.k;
    const r = Math.max(64, 44 / g.k);
    return Math.hypot(x - (tok.x + 18), y - (tok.y + 18)) <= r;
  };

  const stageDown = (e) => {
    if (st.current.drag || e.target.closest(".mbtn")) return;
    if (nearCoin(e)) return tokDown(e);
    // Écran tactile : un tap sur une vignette la sélectionne directement
    if (e.pointerType !== "mouse") {
      const i = hit(e.clientX, e.clientY);
      if (i != null) {
        const k = i === N ? Math.floor(Math.random() * N) : i;
        setSel(k);
        requestAnimationFrame(() => snap(k));
        return;
      }
    }
    clearTimeout(st.current.gunT);
    st.current.gun = true;
    setGun(true);
    placeHand(e);
    const g = geo();
    if (!g) return;
    const x = (e.clientX - g.sr.left) / g.k, y = (e.clientY - g.sr.top) / g.k;
    const shot = document.createElement("img");
    const frames = [A("tir-1.png"), A("tir-2.png"), A("tir-3.png")];
    shot.src = frames[0];
    shot.draggable = false;
    shot.className = "cs-shot";
    Object.assign(shot.style, { left: `${x + 6}px`, top: `${y - 16}px` });
    g.l.appendChild(shot);
    let f = 0;
    const iv = setInterval(() => {
      f = (f + 1) % 3;
      shot.src = frames[f];
    }, 60);
    const dist = W + 20 - x;
    const an = shot.animate(
      [{ transform: "translateX(0)" }, { transform: `translateX(${dist}px)` }],
      { duration: Math.max(250, dist * 0.9), easing: "linear" }
    );
    an.onfinish = () => {
      clearInterval(iv);
      shot.remove();
    };
    st.current.gunT = setTimeout(() => {
      st.current.gun = false;
      setGun(false);
      const p = st.current.ptr;
      if (p && handRef.current)
        handRef.current.style.transform = `translate(${p.x - 54}px,${p.y - 4}px)`;
    }, 380);
  };

  if (!open) return null;
  const charColor = c.color || "#e0242b";

  return (
    <div className="cs-overlay">
      <div
        ref={stageRef}
        className={`cs-stage${portrait ? " cs-stage--portrait" : ""}`}
        style={{ transform: `translate(-50%, -50%) scale(${scale})` }}
        onPointerDown={stageDown}
        onPointerMove={placeHand}
        onPointerLeave={() => {
          if (!st.current.drag && handRef.current) handRef.current.style.opacity = "0";
        }}
      >
        <div className="cs-grid">
          {characters.map((x, i) => (
            <CharacterTile key={x.id ?? i} character={x} index={i} selected={i === sel} />
          ))}
          <div data-char={N} className="cs-tile">
            <span className="cs-q">?</span>
            <span className="cs-name">Aléatoire</span>
          </div>
        </div>

        <div className="cs-bottom">
          <div
            className="cs-p1"
            style={{
              background: `linear-gradient(115deg, ${charColor} 0%, color-mix(in srgb, ${charColor} 72%, #000) 55%, color-mix(in srgb, ${charColor} 38%, #000) 100%)`,
            }}
          >
            <div className="cs-p1-stripes" />
            <div className="cs-p1-circle" />
            <div className="cs-portrait">
              {c.portrait || c.image ? (
                <img src={c.portrait || c.image} alt={c.name} width={290} height={258} fetchPriority="high" />
              ) : (
                <span>portrait</span>
              )}
            </div>
            <span ref={nameRef} className="cs-bigname">
              {c.name}
            </span>
            {login && (
              <div className="cs-plate">
                <span ref={loginRef}>{login}</span>
              </div>
            )}
          </div>
          <div className="cs-right">
            <div
              className="cs-preview"
              style={{
                background: `radial-gradient(circle at 50% 45%, ${charColor}, color-mix(in srgb, ${charColor} 38%, #0a0c28))`,
              }}
            >
              {c.image ? <img src={c.image} alt={c.name} /> : <span>{c.name}</span>}
            </div>
            <div className="cs-actions">
              <span className="cs-kicker">Aperçu du profil</span>
              <MeleeButton text="Valider" selected height={52} onClick={() => onSelect?.(c)} />
              <MeleeButton text="Retour" height={52} onClick={onClose} />
            </div>
          </div>
        </div>

        <div ref={layerRef} className="cs-layer">
          {tok && (
            <div
              ref={coinRef}
              className={`cs-coin${drag ? " drag" : ""}`}
              style={{ left: tok.x, top: tok.y }}
              onPointerDown={tokDown}
            >
              <span className="cs-coin-hit" />
              <img src={A("piece.png")} alt="" draggable="false" />
            </div>
          )}
          <div ref={handRef} className="cs-hand">
            <img
              src={A("main-attrape.png")}
              alt=""
              draggable="false"
              className="cs-h-idle"
              style={{ opacity: drag || gun ? 0 : 1 }}
            />
            <img
              src={A("main-fermee.png")}
              alt=""
              draggable="false"
              className="cs-h-grab"
              style={{ opacity: drag ? 1 : 0 }}
            />
            <img
              src={A("main-pistolet.png")}
              alt=""
              draggable="false"
              className="cs-h-gun"
              style={{ opacity: !drag && gun ? 1 : 0 }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
