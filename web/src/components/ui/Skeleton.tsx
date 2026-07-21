import { cn } from "@/lib/cn";

/**
 * A loading placeholder. It mirrors the shape of the readout it stands in for —
 * a figure skeleton is a figure-sized bar — so the layout doesn't jump when data
 * lands. The pulse is disabled under prefers-reduced-motion (global CSS).
 */
export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-sm bg-panel-2", className)} />;
}

/** A skeleton shaped like a labelled figure (eyebrow + value). */
export function StatSkeleton() {
  return (
    <div className="flex flex-col gap-2">
      <Skeleton className="h-2.5 w-16" />
      <Skeleton className="h-6 w-28" />
    </div>
  );
}

/** A few skeleton rows shaped like a data table. */
export function TableSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="flex flex-col gap-2">
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} className="h-6 w-full" />
      ))}
    </div>
  );
}
