"use client";

import { useState } from "react";
import { Panel } from "@/components/ui/Panel";
import { DataTable, type Column } from "@/components/ui/Table";
import { SignedNumber } from "@/components/ui/SignedNumber";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { IconGaugeEmpty, IconWindow } from "@/components/ui/icons";
import { cn } from "@/lib/cn";
import { formatINR, formatPct } from "@/lib/money";
import { ApiError } from "@/api/client";
import type { AllocationView, PortfolioMetricsView } from "@/api/types";
import { useHoldings } from "../hooks";
import { OBJECTIVES, type Objective } from "../optimizerApi";
import { useOptimizedPortfolio } from "../optimizerHooks";

/** A year of trading data — long enough for a stable covariance estimate,
 *  short enough that it still describes the current market. */
const LOOKBACK_DAYS = 365;
/** No single position above 35% of the target portfolio. */
const MAX_WEIGHT = 0.35;

/**
 * Portfolio optimizer.
 *
 * Answers one question: given what you already own, what mix would have been
 * better, and what would you have to trade to get there? It never places those
 * trades — you do that on the trade desk. Showing the trades rather than
 * executing them keeps the size of the rebalance visible.
 */
export function OptimizerPanel({ id }: { id: string }) {
  const [objective, setObjective] = useState<Objective>("max_sharpe");
  const holdings = useHoldings(id);

  // The backend needs two or more positions to have a covariance to work with.
  // Don't send a request that we know will be refused.
  const holdingCount = holdings.data?.length ?? 0;
  const enabled = holdingCount >= 2;

  const q = useOptimizedPortfolio(id, objective, LOOKBACK_DAYS, MAX_WEIGHT, enabled);
  const chosen = OBJECTIVES.find((o) => o.value === objective);

  return (
    <Panel
      label="Optimizer"
      aside={
        <div className="flex flex-wrap gap-1" role="group" aria-label="Optimization goal">
          {OBJECTIVES.map((o) => (
            <button
              key={o.value}
              type="button"
              onClick={() => setObjective(o.value)}
              aria-pressed={o.value === objective}
              title={o.blurb}
              className={cn(
                "rounded-sm px-1.5 py-0.5 font-mono text-[0.625rem] uppercase tracking-wider transition-colors",
                o.value === objective
                  ? "bg-panel-2 text-fg"
                  : "text-fg-mute hover:text-fg-dim",
              )}
            >
              {o.label}
            </button>
          ))}
        </div>
      }
    >
      <p className="mb-3 text-2xs text-fg-dim">
        {chosen?.blurb} Based on the last year of prices. Suggestions only —
        nothing is traded for you.
      </p>

      {holdings.isLoading ? (
        <Skeleton className="h-40 w-full" />
      ) : !enabled ? (
        <EmptyState icon={<IconGaugeEmpty />} title="Need at least two holdings">
          The optimizer works out how your stocks move relative to each other, so
          it needs at least two. Buy another stock and it will appear here.
        </EmptyState>
      ) : q.isLoading ? (
        <Skeleton className="h-40 w-full" />
      ) : q.isError ? (
        <ErrorState detail={(q.error as ApiError).message} onRetry={() => q.refetch()} />
      ) : q.data ? (
        <div className="flex flex-col gap-5">
          <Comparison
            optimized={q.data.optimized}
            baseline={q.data.equal_weight_baseline}
          />
          <Allocations rows={q.data.allocations} />
          <Trades trades={q.data.trades} />
          {(q.data.notes ?? []).length > 0 && (
            <ul className="flex flex-col gap-1">
              {(q.data.notes ?? []).map((note) => (
                <li key={note} className="text-2xs leading-relaxed text-fg-dim">
                  — {note}
                </li>
              ))}
            </ul>
          )}
          <p className="text-[0.625rem] text-fg-mute">
            Fitted on {q.data.observations} trading days ·{" "}
            {q.data.lookback_days}-day window · max {Math.round(MAX_WEIGHT * 100)}%
            per position
          </p>
        </div>
      ) : null}
    </Panel>
  );
}

/**
 * The optimized portfolio against an equal split of the same stocks.
 *
 * Equal weight is shown on purpose: it is the honest baseline. If the
 * optimizer can't beat "just put the same in everything", it hasn't earned the
 * extra machinery, and you should be able to see that immediately.
 */
function Comparison({
  optimized,
  baseline,
}: {
  optimized: PortfolioMetricsView;
  baseline: PortfolioMetricsView;
}) {
  const rows: { label: string; tip: string; opt: string; base: string }[] = [
    {
      label: "Expected return",
      tip: "Annual return implied by the last year of prices. An estimate, not a promise.",
      opt: formatPct(optimized.expected_return_pct, 1),
      base: formatPct(baseline.expected_return_pct, 1),
    },
    {
      label: "Volatility",
      tip: "How much the portfolio's value swings in a year. Lower is calmer.",
      opt: formatPct(optimized.volatility_pct, 1),
      base: formatPct(baseline.volatility_pct, 1),
    },
    {
      label: "Sharpe",
      tip: "Return earned per unit of risk. The single best summary number — higher is better.",
      opt: optimized.sharpe_ratio.toFixed(2),
      base: baseline.sharpe_ratio.toFixed(2),
    },
    {
      label: "Diversification",
      tip: "1.0 means your holdings move together, so owning several is like owning one. Higher is genuinely spread out.",
      opt: optimized.diversification_ratio.toFixed(2),
      base: baseline.diversification_ratio.toFixed(2),
    },
    {
      label: "Effective holdings",
      tip: "How many positions the portfolio behaves like. Ten stocks with one at 90% behaves like about one.",
      opt: optimized.effective_number_of_assets.toFixed(1),
      base: baseline.effective_number_of_assets.toFixed(1),
    },
    {
      label: "Worst drop",
      tip: "The deepest peak-to-trough fall this mix would have had over the window.",
      opt: formatPct(optimized.max_drawdown_pct, 1),
      base: formatPct(baseline.max_drawdown_pct, 1),
    },
  ];

  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between">
        <h3 className="eyebrow">Suggested vs equal split</h3>
        <span className="text-[0.625rem] text-fg-mute">
          equal split = the baseline to beat
        </span>
      </div>
      <div className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3 lg:grid-cols-6">
        {rows.map((r) => (
          <div key={r.label} className="flex flex-col gap-0.5">
            <span className="eyebrow cursor-help" title={r.tip}>
              {r.label}
            </span>
            <span className="font-mono text-sm text-fg tnum">{r.opt}</span>
            <span className="font-mono text-[0.625rem] text-fg-mute tnum">
              {r.base} equal
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

const allocationColumns: Column<AllocationView>[] = [
  { header: "Symbol", cell: (a) => <span className="text-fg">{a.symbol}</span> },
  {
    header: "Now",
    align: "right",
    cell: (a) => formatPct(a.current_weight_pct ?? 0, 1),
  },
  {
    header: "Suggested",
    align: "right",
    cell: (a) => (
      <span className="text-fg">{formatPct(a.target_weight_pct, 1)}</span>
    ),
  },
  {
    header: "Change",
    align: "right",
    cell: (a) =>
      a.weight_change_pct === null || a.weight_change_pct === undefined ? (
        "—"
      ) : (
        <SignedNumber value={a.weight_change_pct} kind="pct" />
      ),
  },
  {
    header: "Weight",
    width: "8rem",
    cell: (a) => (
      <WeightBar current={a.current_weight_pct ?? 0} target={a.target_weight_pct} />
    ),
  },
  {
    header: "Risk share",
    align: "right",
    cell: (a) => formatPct(a.risk_contribution_pct, 1),
  },
  {
    header: "Volatility",
    align: "right",
    cell: (a) => formatPct(a.annualized_volatility_pct, 1),
  },
];

function Allocations({ rows }: { rows: AllocationView[] }) {
  return (
    <div>
      <h3 className="eyebrow mb-2">Allocation</h3>
      <DataTable
        columns={allocationColumns}
        rows={rows}
        getRowKey={(a) => a.symbol}
        minWidth="44rem"
      />
      <p className="mt-2 text-2xs text-fg-dim">
        <span className="text-fg">Risk share</span> is not the same as weight: a
        small position in a jumpy stock can supply most of the portfolio&apos;s
        risk.
      </p>
    </div>
  );
}

/**
 * Two stacked bars: where the position is now (dim) and where the optimizer
 * would put it (bright). Deliberately not a chart library — it's two divs, and
 * the numeric columns next to it carry the precise values anyway.
 */
function WeightBar({ current, target }: { current: number; target: number }) {
  const scale = (v: number) => `${Math.min(100, Math.max(0, v))}%`;
  return (
    <span className="flex flex-col gap-0.5" aria-hidden="true">
      <span className="block h-1 w-full rounded-sm bg-panel-2">
        <span className="block h-full rounded-sm bg-fg-mute" style={{ width: scale(current) }} />
      </span>
      <span className="block h-1 w-full rounded-sm bg-panel-2">
        <span className="block h-full rounded-sm bg-fg" style={{ width: scale(target) }} />
      </span>
    </span>
  );
}

function Trades({
  trades,
}: {
  trades: { symbol: string; action: string; amount: string; reason: string }[];
}) {
  return (
    <div>
      <h3 className="eyebrow mb-2">To get there</h3>
      {trades.length === 0 ? (
        <EmptyState icon={<IconWindow />} title="Already close enough">
          Your current mix is within a percent of the suggestion. Nothing worth
          trading.
        </EmptyState>
      ) : (
        <ul className="flex flex-col divide-y divide-line">
          {trades.map((t) => (
            <li
              key={`${t.action}-${t.symbol}`}
              className="flex items-start justify-between gap-3 py-2"
            >
              <span className="min-w-0">
                <span
                  className={cn(
                    "font-mono text-2xs uppercase tracking-wider",
                    t.action === "buy" ? "text-up" : "text-down",
                  )}
                >
                  {t.action}
                </span>{" "}
                <span className="text-xs text-fg">{t.symbol}</span>
                <span className="mt-0.5 block text-2xs text-fg-dim">{t.reason}</span>
              </span>
              <span className="shrink-0 font-mono text-xs text-fg tnum">
                {formatINR(t.amount, 0)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
