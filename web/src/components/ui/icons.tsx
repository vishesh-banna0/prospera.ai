/**
 * A tiny hand-drawn icon set. Icons, never emoji (emoji-as-icon is banned in the
 * brief). Line style matches the instrument: 1.5 stroke, no fill, currentColor.
 */
import { cn } from "@/lib/cn";

type IconProps = { className?: string };

function Svg({ className, children }: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={cn("h-5 w-5", className)}
      aria-hidden
    >
      {children}
    </svg>
  );
}

/** No prior analysis yet — an empty gauge dial. */
export function IconGaugeEmpty({ className }: IconProps) {
  return (
    <Svg className={className}>
      <path d="M4 15a8 8 0 0 1 16 0" />
      <path d="M4 15h16" />
      <path d="M12 15l3-3" opacity="0.4" />
    </Svg>
  );
}

/** Needs a key — a keyhole/key. */
export function IconKey({ className }: IconProps) {
  return (
    <Svg className={className}>
      <circle cx="8" cy="8" r="4" />
      <path d="M11 11l7 7" />
      <path d="M16 16l2-2M18 18l2-2" />
    </Svg>
  );
}

/** No data in this window — an empty range bracket. */
export function IconWindow({ className }: IconProps) {
  return (
    <Svg className={className}>
      <path d="M6 4v16M18 4v16" />
      <path d="M9 12h6" opacity="0.5" strokeDasharray="2 2" />
    </Svg>
  );
}

/** A fault — the one error surface uses this. */
export function IconFault({ className }: IconProps) {
  return (
    <Svg className={className}>
      <path d="M12 4l8 14H4z" />
      <path d="M12 10v4" />
      <path d="M12 16.5v.5" />
    </Svg>
  );
}

export function IconRetry({ className }: IconProps) {
  return (
    <Svg className={className}>
      <path d="M20 11a8 8 0 1 0-2 6" />
      <path d="M20 5v6h-6" />
    </Svg>
  );
}
