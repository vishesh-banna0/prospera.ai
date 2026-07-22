/**
 * The one place money and numbers are formatted. Nothing else in the app is
 * allowed to call `toFixed` on a value the user sees. See DESIGN.md §3.
 *
 * Everything is INR. The backend already converts foreign prices to rupees, so
 * the frontend never does FX — it only formats.
 */

export type Sign = "up" | "down" | "flat";

/** Proper typographic minus (U+2212), same width as `+` in tabular figures. */
const MINUS = "−";

/**
 * The API sends money sometimes as a number, sometimes as a decimal *string*
 * (e.g. a quote's `last_price: "2945.60"`), and sometimes null. Normalize to a
 * number, or null when there is genuinely no value.
 */
export function toNumber(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined) return null;
  const n = typeof value === "string" ? Number(value) : value;
  return Number.isFinite(n) ? n : null;
}

/** Which direction a signed value points. Zero is flat, not up. */
export function signOf(value: number): Sign {
  if (value > 0) return "up";
  if (value < 0) return "down";
  return "flat";
}

const inrFull = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const inrFullWhole = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

/**
 * Full rupee amount with Indian grouping: ₹1,23,45,678.00
 * @param decimals show paise (2) or round to whole rupees (0)
 */
export function formatINR(
  value: string | number | null | undefined,
  decimals: 0 | 2 = 2,
): string {
  const n = toNumber(value);
  if (n === null) return "—";
  return (decimals === 0 ? inrFullWhole : inrFull).format(n);
}

/**
 * A headline rupee figure that never overflows its cell: the exact amount when
 * it's short enough, otherwise the compact ladder (₹9.99L cr). Returns `title`
 * with the exact value too, so callers can keep it available on hover. `maxChars`
 * is the widest exact string a headline cell can show before it would collide.
 */
export function formatINRHeadline(
  value: string | number | null | undefined,
  maxChars = 14,
): { text: string; title: string } {
  const full = formatINR(value, 0);
  if (full === "—" || full.length <= maxChars) return { text: full, title: full };
  return { text: formatCompactINR(value), title: full };
}

const plainIN = new Intl.NumberFormat("en-IN", {
  minimumFractionDigits: 0,
  maximumFractionDigits: 4,
});

/** A bare number with Indian grouping and up to 4 dp (share quantities etc.). */
export function formatQty(value: string | number | null | undefined): string {
  const n = toNumber(value);
  if (n === null) return "—";
  return plainIN.format(n);
}

/**
 * Compact rupee for cards and headlines, on the Indian ladder:
 * K (thousand) → L (lakh, 1e5) → Cr (crore, 1e7) → L cr (lakh-crore, 1e12).
 * e.g. ₹2.85L cr · ₹3.20 Cr · ₹8.42 L · ₹12.5K
 *
 * Use this where space is tight. In aligned table columns prefer `formatINR`
 * so decimal points line up.
 */
export function formatCompactINR(value: string | number | null | undefined): string {
  const n = toNumber(value);
  if (n === null) return "—";
  const sign = n < 0 ? MINUS : "";
  const abs = Math.abs(n);

  if (abs >= 1e12) return `${sign}₹${trim(abs / 1e12, 2)}L cr`;
  if (abs >= 1e7) return `${sign}₹${trim(abs / 1e7, 2)} Cr`;
  if (abs >= 1e5) return `${sign}₹${trim(abs / 1e5, 2)} L`;
  if (abs >= 1e3) return `${sign}₹${trim(abs / 1e3, 1)}K`;
  return `${sign}₹${trim(abs, 0)}`;
}

function trim(n: number, maxDp: number): string {
  return n.toLocaleString("en-IN", {
    minimumFractionDigits: 0,
    maximumFractionDigits: maxDp,
  });
}

/**
 * A signed rupee delta with an explicit leading sign: +₹3,20,110 / −₹1,200
 * The sign is always present — direction is never left to color alone.
 */
export function formatSignedINR(
  value: string | number | null | undefined,
  decimals: 0 | 2 = 0,
): string {
  const n = toNumber(value);
  if (n === null) return "—";
  const body = formatINR(Math.abs(n), decimals);
  if (n > 0) return `+${body}`;
  if (n < 0) return `${MINUS}${body}`;
  return body;
}

/**
 * A signed percentage: +2.64% / −1.20% / 0.00%
 * @param value already a percentage (2.64 means 2.64%, not 0.0264)
 */
export function formatSignedPct(
  value: string | number | null | undefined,
  decimals = 2,
): string {
  const n = toNumber(value);
  if (n === null) return "—";
  const body = `${Math.abs(n).toFixed(decimals)}%`;
  if (n > 0) return `+${body}`;
  if (n < 0) return `${MINUS}${body}`;
  return body;
}

/** A plain percentage with no forced sign: 72.0% (for confidence, probability). */
export function formatPct(
  value: string | number | null | undefined,
  decimals = 1,
): string {
  const n = toNumber(value);
  if (n === null) return "—";
  return `${n.toFixed(decimals)}%`;
}

/** A 0–1 ratio shown as a percentage: 0.72 → 72% (confidence, probability). */
export function formatRatioPct(
  value: string | number | null | undefined,
  decimals = 0,
): string {
  const n = toNumber(value);
  if (n === null) return "—";
  return `${(n * 100).toFixed(decimals)}%`;
}

/** Compact plain count: 1.2M, 84.5K, 920 (volume, employees). */
export function formatCompactNumber(value: string | number | null | undefined): string {
  const n = toNumber(value);
  if (n === null) return "—";
  return new Intl.NumberFormat("en-IN", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(n);
}
