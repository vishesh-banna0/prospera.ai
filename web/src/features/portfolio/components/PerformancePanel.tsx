"use client";

import { Panel, Stat } from "@/components/ui/Panel";
import { SignedNumber } from "@/components/ui/SignedNumber";
import { StatSkeleton } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/States";
import { formatINR } from "@/lib/money";
import { ApiError } from "@/api/client";
import { usePerformance } from "../hooks";

/** The portfolio's vital signs. Net liquidation leads; the rest supports it. */
export function PerformancePanel({ id }: { id: string }) {
  const q = usePerformance(id);

  return (
    <Panel label="Performance" aside={<Refresh onClick={() => q.refetch()} busy={q.isFetching} />}>
      {q.isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }, (_, i) => (
            <StatSkeleton key={i} />
          ))}
        </div>
      ) : q.isError ? (
        <ErrorState detail={(q.error as ApiError).message} onRetry={() => q.refetch()} />
      ) : q.data ? (
        <div className="grid gap-x-6 gap-y-4 sm:grid-cols-2 lg:grid-cols-4">
          <Stat
            label="Net liquidation"
            value={formatINR(q.data.portfolio_value, 0)}
            className="lg:col-span-1"
          />
          <Stat label="Cash" value={formatINR(q.data.cash_balance, 0)} />
          <Stat label="Invested" value={formatINR(q.data.invested_amount, 0)} />
          <div className="flex flex-col gap-1">
            <span className="eyebrow">Unrealized P&amp;L</span>
            <span className="text-xl leading-none">
              <SignedNumber value={q.data.unrealized_pnl} kind="inr" />
            </span>
            <span className="text-2xs">
              <SignedNumber value={q.data.return_percentage} kind="pct" />
            </span>
          </div>
        </div>
      ) : null}
    </Panel>
  );
}

function Refresh({ onClick, busy }: { onClick: () => void; busy: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="font-mono text-2xs uppercase tracking-wider text-fg-mute hover:text-fg-dim disabled:opacity-50"
      disabled={busy}
    >
      {busy ? "…" : "refresh"}
    </button>
  );
}
