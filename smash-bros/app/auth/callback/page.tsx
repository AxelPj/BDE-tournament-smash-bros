"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

function CallbackHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const calledRef = useRef(false);

  useEffect(() => {
    if (calledRef.current) return;
    calledRef.current = true;

    const code = searchParams.get("code");
    const state = searchParams.get("state");

    if (!code || !state) {
      setError("Paramètres de retour 42 manquants (code ou state).");
      return;
    }

    const redirectUri = `${window.location.origin}/auth/callback`;

    fetch("/api/auth/oauth/42/callback", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        code,
        state,
        redirect_uri: redirectUri,
      }),
    })
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json().catch(() => null);
          throw new Error(data?.detail || "Échec de l'authentification 42.");
        }
        router.replace("/");
      })
      .catch((err: Error) => {
        setError(err.message);
      });
  }, [router, searchParams]);

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        background: "#07070c",
        color: "#fff",
        fontFamily: "sans-serif",
      }}
    >
      {error ? (
        <div style={{ textAlign: "center" }}>
          <p style={{ color: "#ff5555", marginBottom: "1rem" }}>{error}</p>
          <Link href="/" style={{ color: "#ffd000", textDecoration: "underline" }}>
            Retour à l&apos;accueil
          </Link>
        </div>
      ) : (
        <p>Connexion avec 42 en cours...</p>
      )}
    </main>
  );
}

export default function OAuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <main
          style={{
            minHeight: "100vh",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "#07070c",
            color: "#fff",
          }}
        >
          <p>Chargement...</p>
        </main>
      }
    >
      <CallbackHandler />
    </Suspense>
  );
}
