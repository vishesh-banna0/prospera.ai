import { cn } from "@/lib/cn";
import { Button } from "./Button";
import { IconFault, IconRetry } from "./icons";

/**
 * Empty and error states. The brief calls for three empty states that read
 * DIFFERENTLY — an invitation, a missing-key notice, and an out-of-range notice —
 * so this component leads with intent, not mood. An empty screen is an invitation
 * to act; an error says what happened and how to fix it, in the machine's voice.
 */

export function EmptyState({
  icon,
  title,
  children,
  action,
  tone = "neutral",
  className,
}: {
  icon: React.ReactNode;
  title: string;
  children?: React.ReactNode;
  action?: React.ReactNode;
  tone?: "neutral" | "warn";
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center rounded border border-dashed px-6 py-10 text-center",
        tone === "warn" ? "border-warn/40" : "border-line-2",
        className,
      )}
    >
      <div className={cn("mb-3", tone === "warn" ? "text-warn" : "text-fg-mute")}>{icon}</div>
      <h3 className="font-display text-sm font-semibold text-fg">{title}</h3>
      {children && <div className="mt-1.5 max-w-sm text-2xs leading-relaxed text-fg-dim">{children}</div>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

/**
 * THE one error surface. The backend's `detail` is shown verbatim because its
 * messages are specific. It never apologizes and is never vague.
 */
export function ErrorState({
  detail,
  onRetry,
  className,
}: {
  detail: string;
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <div
      role="alert"
      className={cn(
        "flex items-start gap-3 rounded border border-down/40 bg-down/5 px-3 py-3",
        className,
      )}
    >
      <IconFault className="mt-0.5 h-4 w-4 shrink-0 text-down" />
      <div className="min-w-0 flex-1">
        <p className="font-mono text-2xs font-medium uppercase tracking-wider text-down">Fault</p>
        <p className="mt-1 break-words text-xs text-fg">{detail}</p>
      </div>
      {onRetry && (
        <Button variant="ghost" size="sm" onClick={onRetry} className="shrink-0">
          <IconRetry className="h-3.5 w-3.5" />
          Retry
        </Button>
      )}
    </div>
  );
}
