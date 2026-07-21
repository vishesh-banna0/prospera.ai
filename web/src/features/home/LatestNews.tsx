"use client";

import Link from "next/link";
import { Panel } from "@/components/ui/Panel";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { IconWindow } from "@/components/ui/icons";
import { ApiError } from "@/api/client";
import { useArticles } from "@/features/news/hooks";

const timeFmt = new Intl.DateTimeFormat("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", hour12: false });
function fmt(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : timeFmt.format(d);
}

/** A short feed of the latest collected headlines. */
export function LatestNews() {
  const q = useArticles({ limit: 6 });
  const rows = q.data?.articles ?? [];

  return (
    <Panel
      label="The tape"
      aside={
        <Link href="/news" className="font-mono text-[0.625rem] uppercase tracking-wider text-fg-mute hover:text-fg-dim">
          all →
        </Link>
      }
      bodyClassName={rows.length ? "p-0" : "p-3"}
    >
      {q.isLoading ? (
        <TableSkeleton rows={5} />
      ) : q.isError ? (
        <ErrorState detail={(q.error as ApiError).message} onRetry={() => q.refetch()} />
      ) : rows.length === 0 ? (
        <EmptyState icon={<IconWindow />} title="No news yet">
          Sync the news warehouse on the backend to fill the tape.
        </EmptyState>
      ) : (
        <ul>
          {rows.map((a) => (
            <li key={a.article_id} className="border-b border-line px-3 py-2 last:border-0 hover:bg-panel-2/40">
              <a href={a.url} target="_blank" rel="noopener noreferrer" className="text-xs leading-snug text-fg hover:underline">
                {a.title}
              </a>
              <div className="mt-0.5 font-mono text-[0.625rem] text-fg-mute tnum">
                {a.source} · {fmt(a.published_at)}
              </div>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
