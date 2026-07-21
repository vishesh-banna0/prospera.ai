"use client";

import Link from "next/link";
import { Panel } from "@/components/ui/Panel";
import { Badge, toneForVerdict } from "@/components/ui/Badge";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { IconGaugeEmpty } from "@/components/ui/icons";
import { formatPct } from "@/lib/money";
import { ApiError } from "@/api/client";
import { useSignals } from "@/features/intelligence/hooks";

/** The most recent fused Buy/Hold/Sell calls across analyzed symbols. */
export function MachineCalls() {
  const q = useSignals();
  const rows = (q.data?.signals ?? []).slice(0, 6);

  return (
    <Panel
      label="Latest calls"
      aside={
        <Link href="/intelligence" className="font-mono text-[0.625rem] uppercase tracking-wider text-fg-mute hover:text-fg-dim">
          all →
        </Link>
      }
      bodyClassName={rows.length ? "p-0" : "p-3"}
    >
      {q.isLoading ? (
        <TableSkeleton rows={4} />
      ) : q.isError ? (
        <ErrorState detail={(q.error as ApiError).message} onRetry={() => q.refetch()} />
      ) : rows.length === 0 ? (
        <EmptyState icon={<IconGaugeEmpty />} title="No calls yet">
          Analyze a symbol to see the machine&rsquo;s Buy/Hold/Sell here.
        </EmptyState>
      ) : (
        <ul>
          {rows.map((s) => (
            <li key={s.symbol}>
              <Link
                href={`/intelligence/${encodeURIComponent(s.symbol)}`}
                className="flex items-center gap-3 border-b border-line px-3 py-2 last:border-0 hover:bg-panel-2/40"
              >
                <span className="w-24 shrink-0 font-mono text-xs text-fg">{s.symbol}</span>
                <Badge tone={toneForVerdict(s.action)}>{s.action}</Badge>
                <span className="ml-auto font-mono text-2xs text-fg-mute tnum">
                  conf {formatPct(s.confidence * 100, 0)}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
