import { cn } from "@/lib/cn";

/**
 * A verdict chip: Buy/Hold/Sell, bullish/bearish/neutral, a rating. Direction is
 * carried by the border + text color AND the word itself — never color alone.
 * A leading tick mark reinforces the state for a fast scan down a column.
 */

export type BadgeTone = "up" | "down" | "hold" | "neutral" | "warn";

const styles: Record<BadgeTone, string> = {
  up: "border-up/40 text-up",
  down: "border-down/40 text-down",
  hold: "border-hold/40 text-hold",
  neutral: "border-line-2 text-fg-dim",
  warn: "border-warn/40 text-warn",
};

const tick: Record<BadgeTone, string> = {
  up: "▲",
  down: "▼",
  hold: "■",
  neutral: "•",
  warn: "!",
};

export interface BadgeProps {
  children: React.ReactNode;
  tone?: BadgeTone;
  withTick?: boolean;
  className?: string;
}

export function Badge({ children, tone = "neutral", withTick = true, className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-sm border bg-panel-2/40 px-2 py-0.5",
        "font-mono text-2xs font-medium uppercase tracking-wider",
        styles[tone],
        className,
      )}
    >
      {withTick && (
        <span aria-hidden className="text-[0.7em] leading-none">
          {tick[tone]}
        </span>
      )}
      {children}
    </span>
  );
}

/** Map a backend action/stance string to a badge tone. */
export function toneForVerdict(verdict: string): BadgeTone {
  const v = verdict.trim().toLowerCase();
  if (["buy", "bullish", "strong buy", "accumulate"].includes(v)) return "up";
  if (["sell", "bearish", "strong sell", "reduce"].includes(v)) return "down";
  if (["hold", "neutral"].includes(v)) return "hold";
  return "neutral";
}
