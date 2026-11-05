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
/** @param {Record<string, any>} props */
export default function SmashIntro({
  webmSrc,
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
    if (!ctx) return;

    const lowPower = (navigator.hardwareConcurrency || 4) <= 4;
    const particleCount = lowPower ? 35 : 55;
    const maxDpr = lowPower ? 1 : 1.5;
    const frameDuration = 1000 / 30;
    let W = 0, H = 0, raf = 0, lastFrame = 0;
    let visible = document.visibilityState === "visible";

    const size = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, maxDpr);
      W = cv.clientWidth; H = cv.clientHeight;
      cv.width = W * dpr; cv.height = H * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    size();
    window.addEventListener("resize", size);

    // Une seule texture est réutilisée pour chaque braise au lieu de recréer
    // un dégradé radial 30 fois par seconde.
    const ember = document.createElement("canvas");
    ember.width = ember.height = 32;
    const emberCtx = ember.getContext("2d");
    if (!emberCtx) return;
    const gradient = emberCtx.createRadialGradient(16, 16, 0, 16, 16, 16);
    gradient.addColorStop(0, "rgba(255,220,140,0.9)");
    gradient.addColorStop(0.4, "rgba(255,120,30,0.5)");
    gradient.addColorStop(1, "rgba(255,60,0,0)");
    emberCtx.fillStyle = gradient;
    emberCtx.fillRect(0, 0, 32, 32);

    const spawn = () => ({
      x: W * (0.25 + Math.random() * 0.5), y: H * (0.55 + Math.random() * 0.35),
      vx: (Math.random() - 0.5) * 0.4, vy: -(0.4 + Math.random() * 1.2),
      r: 0.6 + Math.random() * 2.2, life: 0, max: 120 + Math.random() * 160,
    });
    const P = Array.from({ length: particleCount }, () => {
      const p = spawn();
      p.life = Math.random() * p.max;
      return p;
    });
    const tick = (now) => {
      if (!visible) {
        raf = 0;
        return;
      }
      if (now - lastFrame < frameDuration) {
        raf = requestAnimationFrame(tick);
        return;
      }
      lastFrame = now;
      ctx.clearRect(0, 0, W, H);
      ctx.globalCompositeOperation = "lighter";
      for (const p of P) {
        p.life++;
        p.x += p.vx + Math.sin((p.life + p.r * 40) * 0.05) * 0.3;
        p.y += p.vy;
        const k = 1 - p.life / p.max;
        if (k <= 0) { Object.assign(p, spawn()); continue; }
        const size = p.r * 8;
        ctx.globalAlpha = k;
        ctx.drawImage(ember, p.x - size / 2, p.y - size / 2, size, size);
      }
      ctx.globalAlpha = 1;
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    const onVisibilityChange = () => {
      visible = document.visibilityState === "visible";
      if (visible && !raf) {
        lastFrame = 0;
        raf = requestAnimationFrame(tick);
      }
    };
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", size);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, []);

  return (
    <section className={`smash-intro${open ? " is-open" : ""}`}>
      <video
        ref={videoRef}
        className="smash-intro__video"
        autoPlay muted loop playsInline preload="metadata"
        aria-label="Logo en flammes"
        onClick={handleOpen}
        onLoadedData={() => setError(false)}
        onCanPlay={() => setError(false)}
        onError={() => setError(true)}
      >
        {mp4Src && <source src={mp4Src} type="video/mp4" />}
        {webmSrc && <source src={webmSrc} type="video/webm" />}
      </video>
      <div className="smash-intro__vignette" />
      <canvas ref={canvasRef} className="smash-intro__embers" />

      <button className="smash-intro__cta" type="button" onClick={handleOpen}>
        <span className="smash-intro__dot" aria-hidden="true" />
        <span className="smash-intro__cta-text">{ctaText}</span>
      </button>

      {children}

      {error && (
        <p className="smash-intro__error">
          La vidéo n&apos;a pas pu être chargée. Vérifie les chemins <b>{webmSrc}</b> et <b>{mp4Src}</b>.
        </p>
      )}
    </section>
  );
}
