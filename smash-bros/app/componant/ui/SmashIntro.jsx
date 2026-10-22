import { useEffect, useRef, useState } from "react";
import "../css/SmashIntro.css";

/**
 * Accueil : vidéo zoomée sur le logo en feu (muette, en boucle) + braises.
 * Au clic sur "Cliquer" (ou sur la vidéo) : dézoom, le son se lance, la vidéo tourne en boucle.
 *
 * Props :
 *  - webmSrc, mp4Src (string)  chemins de la vidéo (ex: "/smash-video.webm", "/smash-video.mp4")
 *  - ctaText         (string)  texte du bouton d'appel ("Cliquer" par défaut)
 *  - onOpen          (func)    appelé au moment du dézoom
 *  - children                  contenu affiché en haut à droite après le dézoom (ex: <MeleeButton text="Connexion" />)
 */
export default function SmashIntro({
  webmSrc = "/smash-video.webm",
  mp4Src = "/smash-video.mp4",
  ctaText = "Cliquer",
  onOpen,
  children,
}) {
  const [open, setOpen] = useState(false);
  const [error, setError] = useState(false);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  // lecture muette en boucle au chargement = logo animé
  useEffect(() => {
    videoRef.current?.play().catch(() => {});
  }, []);

  const handleOpen = () => {
    if (open) return;
    setOpen(true);
    const v = videoRef.current;
    if (v) {
      v.muted = false;
      v.volume = 1;
      v.loop = true;
      v.play().catch(() => {
        v.muted = true;
        v.play().catch(() => {});
      });
    }
    onOpen?.();
  };

  // braises
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const cv = canvasRef.current;
    if (!cv) return;
    const ctx = cv.getContext("2d");
    let W = 0, H = 0, raf = 0;
    const size = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      W = cv.clientWidth; H = cv.clientHeight;
      cv.width = W * dpr; cv.height = H * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    size();
    window.addEventListener("resize", size);
    const spawn = () => ({
      x: W * (0.25 + Math.random() * 0.5), y: H * (0.55 + Math.random() * 0.35),
      vx: (Math.random() - 0.5) * 0.4, vy: -(0.4 + Math.random() * 1.2),
      r: 0.6 + Math.random() * 2.2, life: 0, max: 120 + Math.random() * 160,
    });
    const P = Array.from({ length: 70 }, () => { const p = spawn(); p.life = Math.random() * p.max; return p; });
    const tick = () => {
      ctx.clearRect(0, 0, W, H);
      ctx.globalCompositeOperation = "lighter";
      for (const p of P) {
        p.life++;
        p.x += p.vx + Math.sin((p.life + p.r * 40) * 0.05) * 0.3;
        p.y += p.vy;
        const k = 1 - p.life / p.max;
        if (k <= 0) { Object.assign(p, spawn()); continue; }
        const g = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 4);
        g.addColorStop(0, `rgba(255,220,140,${0.9 * k})`);
        g.addColorStop(0.4, `rgba(255,120,30,${0.5 * k})`);
        g.addColorStop(1, "rgba(255,60,0,0)");
        ctx.fillStyle = g;
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r * 4, 0, Math.PI * 2); ctx.fill();
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => { cancelAnimationFrame(raf); window.removeEventListener("resize", size); };
  }, []);

  return (
    <section className={`smash-intro${open ? " is-open" : ""}`}>
      <video
        ref={videoRef}
        className="smash-intro__video"
        autoPlay muted loop playsInline preload="auto"
        aria-label="Logo en flammes"
        onClick={handleOpen}
        onError={() => setError(true)}
      >
        <source src={webmSrc} type="video/webm" />
        <source src={mp4Src} type="video/mp4" onError={() => setError(true)} />
      </video>
      <div className="smash-intro__vignette" />
      <canvas ref={canvasRef} className="smash-intro__embers" />

      <button className="smash-intro__cta" type="button" onClick={handleOpen}>
        <span className="smash-intro__dot" aria-hidden="true" />
        <span className="smash-intro__cta-text">{ctaText}</span>
      </button>

      {children && <div className="smash-intro__actions">{children}</div>}

      {error && (
        <p className="smash-intro__error">
          La vidéo n'a pas pu être chargée. Vérifie les chemins <b>{webmSrc}</b> et <b>{mp4Src}</b>.
        </p>
      )}
    </section>
  );
}
