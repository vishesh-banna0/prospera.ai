"use client";

import { Badge } from "@/components/ui/Badge";
import type { NewsArticleView } from "@/api/types";

const dateFmt = new Intl.DateTimeFormat("en-IN", {
  day: "2-digit",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});
function fmt(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : dateFmt.format(d);
}

export function ArticleCard({ a }: { a: NewsArticleView }) {
  return (
    <article className="border-b border-line px-3 py-3 last:border-0 hover:bg-panel-2/40">
      <div className="mb-1 flex flex-wrap items-center gap-2">
        <Badge tone="neutral" withTick={false}>{a.category}</Badge>
        <span className="font-mono text-[0.625rem] uppercase tracking-wider text-fg-mute">{a.source}</span>
        <span className="font-mono text-[0.625rem] text-fg-mute tnum">{fmt(a.published_at)}</span>
      </div>
      <a
        href={a.url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-sm font-medium leading-snug text-fg hover:underline"
      >
        {a.title}
      </a>
      {a.summary && <p className="mt-1 line-clamp-2 text-2xs leading-relaxed text-fg-dim">{a.summary}</p>}
      {(a.symbols ?? []).length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1">
          {(a.symbols ?? []).slice(0, 6).map((s) => (
            <span key={s} className="rounded-sm border border-line px-1.5 py-0.5 font-mono text-[0.625rem] text-fg-dim">
              {s}
            </span>
          ))}
        </div>
      )}
    </article>
  );
}
