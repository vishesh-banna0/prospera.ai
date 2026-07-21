"use client";

import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { formatPct } from "@/lib/money";
import type { EventView } from "@/api/types";

const dateFmt = new Intl.DateTimeFormat("en-IN", { day: "2-digit", month: "short", year: "2-digit" });
function fmt(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : dateFmt.format(d);
}

function sentimentTone(sentiment: string): BadgeTone {
  const s = sentiment.toLowerCase();
  if (["positive", "bullish"].includes(s)) return "up";
  if (["negative", "bearish"].includes(s)) return "down";
  return "hold";
}

export function EventCard({ e }: { e: EventView }) {
  return (
    <article className="border-b border-line px-3 py-3 last:border-0 hover:bg-panel-2/40">
      <div className="mb-1 flex flex-wrap items-center gap-2">
        <Badge tone="neutral" withTick={false}>{e.event_type}</Badge>
        <Badge tone={sentimentTone(e.sentiment)}>{e.sentiment}</Badge>
        <span className="font-mono text-[0.625rem] uppercase tracking-wider text-fg-mute">
          {e.importance}
        </span>
        <span className="font-mono text-[0.625rem] text-fg-mute tnum">{fmt(e.event_date)}</span>
        <span className="ml-auto font-mono text-[0.625rem] text-fg-mute tnum">
          conf {formatPct(e.confidence * 100, 0)}
        </span>
      </div>
      <p className="text-sm leading-snug text-fg">{e.headline}</p>
      {(e.symbols ?? []).length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1">
          {(e.symbols ?? []).slice(0, 6).map((s) => (
            <span key={s} className="rounded-sm border border-line px-1.5 py-0.5 font-mono text-[0.625rem] text-fg-dim">
              {s}
            </span>
          ))}
        </div>
      )}
    </article>
  );
}
