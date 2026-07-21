import { cn } from "@/lib/cn";

/**
 * A bordered instrument panel with a small engraved eyebrow label. The base
 * surface of nearly everything in the app. Barely-rounded corners (machined),
 * never a soft pill or a drop shadow.
 */
export function Panel({
  label,
  aside,
  children,
  className,
  bodyClassName,
}: {
  label?: string;
  aside?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <section className={cn("rounded border border-line bg-panel", className)}>
      {(label || aside) && (
        <div className="flex items-center justify-between gap-3 border-b border-line px-3 py-2">
          {label ? <h2 className="eyebrow">{label}</h2> : <span />}
          {aside}
        </div>
      )}
      <div className={cn("p-3", bodyClassName)}>{children}</div>
    </section>
  );
}

/**
 * A labelled figure — the workhorse readout. Eyebrow label, a big mono value,
 * and an optional signed delta line beneath it.
 */
export function Stat({
  label,
  value,
  sub,
  className,
}: {
  label: string;
  value: React.ReactNode;
  sub?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <span className="eyebrow">{label}</span>
      <span className="font-mono text-xl leading-none text-fg tnum">{value}</span>
      {sub && <span className="text-2xs text-fg-dim">{sub}</span>}
    </div>
  );
}
