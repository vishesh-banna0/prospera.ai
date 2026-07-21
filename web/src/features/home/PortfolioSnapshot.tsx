"use client";

import Link from "next/link";
import { Panel } from "@/components/ui/Panel";
import { SignedNumber } from "@/components/ui/SignedNumber";
import { StatSkeleton } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/States";
import { formatINR } from "@/lib/money";
import { ApiError } from "@/api/client";
import { usePortfolioRegistry } from "@/features/portfolio/registry";
import { usePerformance } from "@/features/portfolio/hooks";

/** Home snapshot of the first portfolio in the local registry. */
export function PortfolioSnapshot() {
  const { list } = usePortfolioRegistry();

  if (list === null) {
    return (
      <Panel label="Portfolio">
        <StatSkeleton />
      </Panel>
    );
  }

  const first = list[0];
  if (!first) {
    return (
      <Panel label="Portfolio">
        <div className="flex flex-col items-start gap-2 py-1">
          <p className="text-sm text-fg-dim">No portfolio yet.</p>
          <Link
            href="/portfolio"
            className="rounded border border-fg bg-fg px-3 py-1.5 text-xs font-medium text-ink hover:bg-fg/90"
          >
            Create your first portfolio →
          </Link>
        </div>
      </Panel>
    );
  }

  return <SnapshotCard id={first.id} name={first.name} extra={list.length - 1} />;
}

function SnapshotCard({ id, name, extra }: { id: string; name: string; extra: number }) {
  const q = usePerformance(id);

  return (
    <Panel
      label="Portfolio"
      aside={
        <Link href="/portfolio" className="font-mono text-[0.625rem] uppercase tracking-wider text-fg-mute hover:text-fg-dim">
          open desk →
        </Link>
      }
    >
      <div className="mb-3 flex items-baseline gap-2">
        <span className="text-sm font-medium text-fg">{name}</span>
        {extra > 0 && <span className="font-mono text-2xs text-fg-mute">+{extra} more</span>}
      </div>

      {q.isLoading ? (
        <StatSkeleton />
      ) : q.isError ? (
        <ErrorState detail={(q.error as ApiError).message} onRetry={() => q.refetch()} />
      ) : q.data ? (
        <div className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-4">
          <Item label="Net liquidation" value={formatINR(q.data.portfolio_value, 0)} />
          <Item label="Cash" value={formatINR(q.data.cash_balance, 0)} />
          <div className="flex flex-col gap-1">
            <span className="eyebrow">Unrealized</span>
            <span className="text-sm">
              <SignedNumber value={q.data.unrealized_pnl} kind="inr" />
            </span>
          </div>
          <div className="flex flex-col gap-1">
            <span className="eyebrow">Return</span>
            <span className="text-sm">
              <SignedNumber value={q.data.return_percentage} kind="pct" />
            </span>
          </div>
        </div>
      ) : null}
    </Panel>
  );
}

function Item({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="eyebrow">{label}</span>
      <span className="font-mono text-sm text-fg tnum">{value}</span>
    </div>
  );
}
