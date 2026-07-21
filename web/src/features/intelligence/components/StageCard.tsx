"use client";

import { cn } from "@/lib/cn";
import { ErrorState } from "@/components/ui/States";
import type { StageStatus } from "../useAnalyze";

/**
 * One link in the Analyze chain. The numbered markers (01–04) are earned here:
 * this is a real ordered pipeline where each stage feeds the next, so the order
 * is information, not decoration. A connective line runs the chain top to bottom
 * and "lights" as data flows through.
 */
export function StageCard({
  index,
  title,
  feeds,
  status,
  error,
  isLast,
  children,
}: {
  index: string;
  title: string;
  feeds?: string;
  status: StageStatus;
  error: string | null;
  isLast?: boolean;
  children: React.ReactNode;
}) {
  const done = status === "done";
  const active = status === "running";

  return (
    <div className="relative flex gap-3 sm:gap-4">
      <div className="flex flex-col items-center">
        <div
          className={cn(
            "flex h-7 w-7 shrink-0 items-center justify-center rounded-full border font-mono text-2xs tnum transition-colors",
            done && "border-fg text-fg",
            active && "border-fg-dim text-fg-dim",
            status === "error" && "border-down text-down",
            status === "idle" && "border-line-2 text-fg-mute",
          )}
        >
          {index}
        </div>
        {!isLast && (
          <div
            className={cn("my-1 w-px flex-1 transition-colors", done ? "bg-fg-dim" : "bg-line")}
          />
        )}
      </div>

      <div className="min-w-0 flex-1 pb-6">
        <div className="mb-2 flex items-center justify-between gap-3">
          <div className="flex items-baseline gap-2">
            <h3 className="eyebrow">{title}</h3>
            {feeds && status === "idle" && (
              <span className="font-mono text-[0.625rem] text-fg-mute">→ {feeds}</span>
            )}
          </div>
          <StatusPill status={status} />
        </div>

        <div className="rounded border border-line bg-panel p-3">
          {status === "idle" && (
            <p className="text-2xs text-fg-mute">Queued — runs after the previous stage.</p>
          )}
          {status === "running" && <Running />}
          {status === "error" && error && <ErrorState detail={error} />}
          {done && <div className="animate-count-in">{children}</div>}
        </div>
      </div>
    </div>
  );
}

function StatusPill({ status }: { status: StageStatus }) {
  const map: Record<StageStatus, { label: string; cls: string }> = {
    idle: { label: "queued", cls: "text-fg-mute" },
    running: { label: "computing", cls: "text-fg-dim" },
    done: { label: "done", cls: "text-fg-dim" },
    error: { label: "failed", cls: "text-down" },
  };
  const { label, cls } = map[status];
  return (
    <span className={cn("flex items-center gap-1.5 font-mono text-[0.625rem] uppercase tracking-wider", cls)}>
      {status === "running" && <Spinner />}
      {label}
    </span>
  );
}

function Running() {
  return (
    <div className="flex items-center gap-2 text-2xs text-fg-dim">
      <Spinner />
      <span>Computing…</span>
    </div>
  );
}

function Spinner() {
  return (
    <svg className="h-3 w-3 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" opacity="0.25" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}
