import { cn } from "@/lib/cn";
import { formatSignedINR, formatSignedPct, signOf, type Sign } from "@/lib/money";

/**
 * A signed value that encodes direction FOUR ways at once — glyph, sign, color,
 * and (in a column) position. Never color alone. See DESIGN.md §1.
 *
 *   <SignedNumber value={2.64} kind="pct" />     → ▲ +2.64%   (green)
 *   <SignedNumber value={-320110} kind="inr" />  → ▼ −₹3,20,110 (red)
 */

type Kind = "pct" | "inr";

const glyph: Record<Sign, string> = { up: "▲", down: "▼", flat: "—" };
const toneClass: Record<Sign, string> = {
  up: "text-up",
  down: "text-down",
  flat: "text-hold",
};

export interface SignedNumberProps {
  value: number | string | null | undefined;
  kind: Kind;
  /** paise for INR / decimal places for pct */
  decimals?: number;
  withGlyph?: boolean;
  className?: string;
}

export function SignedNumber({
  value,
  kind,
  decimals,
  withGlyph = true,
  className,
}: SignedNumberProps) {
  const n = typeof value === "string" ? Number(value) : value;
  if (n === null || n === undefined || !Number.isFinite(n)) {
    return <span className={cn("font-mono text-fg-mute tnum", className)}>—</span>;
  }

  const sign = signOf(n);
  const text =
    kind === "pct"
      ? formatSignedPct(n, decimals ?? 2)
      : formatSignedINR(n, (decimals ?? 0) as 0 | 2);

  return (
    <span className={cn("inline-flex items-baseline gap-1 font-mono tnum", toneClass[sign], className)}>
      {withGlyph && (
        <span aria-hidden className="text-[0.7em] leading-none">
          {glyph[sign]}
        </span>
      )}
      <span>{text}</span>
    </span>
  );
}
