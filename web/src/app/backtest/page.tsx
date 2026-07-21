"use client";

import { Panel } from "@/components/ui/Panel";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { IconWindow } from "@/components/ui/icons";
import { ApiError } from "@/api/client";
import { useBacktest } from "@/features/backtest/hooks";
import { BacktestForm } from "@/features/backtest/components/BacktestForm";
import { BacktestResult } from "@/features/backtest/components/BacktestResult";

export default function BacktestPage() {
  const bt = useBacktest();

  return (
    <div className="mx-auto max-w-5xl px-4 py-5 sm:px-6">
      <header className="mb-4">
        <p className="eyebrow">Machine · Backtest</p>
        <h1 className="mt-1 font-display text-xl font-bold text-fg">What if I&rsquo;d invested?</h1>
        <p className="mt-1 max-w-2xl text-2xs text-fg-dim">
          Replay history: put a lump sum or a monthly SIP into a stock over a window
          and see what it would have become — with the return and risk to match.
        </p>
      </header>

      <div className="flex flex-col gap-4">
        <BacktestForm onRun={(input) => bt.mutate(input)} pending={bt.isPending} />

        {bt.isPending ? (
          <LoadingResult />
        ) : bt.isError ? (
          <ErrorState detail={(bt.error as ApiError).message} />
        ) : bt.data ? (
          <BacktestResult r={bt.data} />
        ) : (
          <EmptyState icon={<IconWindow />} title="No simulation yet" className="mt-2">
            Set a symbol, an amount, and a date window above, then run a simulation.
            Recent windows work best — history is filled on demand.
          </EmptyState>
        )}
      </div>
    </div>
  );
}

function LoadingResult() {
  return (
    <div className="flex flex-col gap-4">
      <Panel label="Result">
        <Skeleton className="h-16 w-64" />
      </Panel>
      <Panel label="Invested vs value">
        <Skeleton className="h-72 w-full" />
      </Panel>
    </div>
  );
}
