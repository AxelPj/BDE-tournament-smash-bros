/**
 * Formateurs standard Intl singleton (instanciés une seule fois en mémoire)
 * et utilitaires partagés entre les composants du frontend.
 */

const FR_NUMBER = new Intl.NumberFormat("fr-FR");
const FR_SHORT_DATE = new Intl.DateTimeFormat("fr-FR", {
  weekday: "short",
  day: "numeric",
  month: "short",
});

export const fmt = (n: number | string | null | undefined): string =>
  FR_NUMBER.format(Number(n) || 0);

export const formatShortDate = (isoOrDate: string | Date): string => {
  const d = typeof isoOrDate === "string" ? new Date(isoOrDate) : isoOrDate;
  return Number.isNaN(d.getTime()) ? "" : FR_SHORT_DATE.format(d);
};

export async function apiJson<T = any>(
  url: string,
  init?: RequestInit
): Promise<T | null> {
  const res = await fetch(url, {
    ...init,
    headers: {
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });
  if (!res.ok) return null;
  if (res.status === 204) return true as unknown as T;
  return res.json();
}
