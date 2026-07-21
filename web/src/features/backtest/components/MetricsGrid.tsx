"use client";

import { SignedNumber } from "@/components/ui/SignedNumber";
import { formatINR, formatPct } from "@/lib/money";
import type { MetricsView } from "@/api/types";

/**
 * The ten backtest metrics. Return metrics get a signed value+color; risk metrics
 * are neutral (a high volatility isn't "good" or "bad", it's just risk). Each
 * label carries a plain-English tooltip from the glossary, since the terms matter.
 */
export function MetricsGrid({ m }: { m: MetricsView }) {
  return (
    <div className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3 lg:grid-cols-5">
      <Tile label="Total invested" tip="What you put in over the whole period.">
        {formatINR(m.total_invested, 0)}
      </Tile>
      <Tile label="Final value" tip="What the investment was worth at the end.">
        {formatINR(m.final_value, 0)}
      </Tile>
      <Tile label="Profit" tip="Final value minus what you invested.">
        <SignedNumber value={m.profit} kind="inr" decimals={0} />
      </Tile>
      <Tile label="Total return" tip="Profit as a percentage of what you invested.">
        <SignedNumber value={m.total_return_pct} kind="pct" />
      </Tile>
      <Tile label="CAGR" tip="Compound annual growth rate — the smoothed yearly growth.">
        <SignedNumber value={m.cagr_pct} kind="pct" />
      </Tile>
      <Tile label="XIRR" tip="Annualized return that accounts for money added at different times — the right measure for a SIP.">
        <SignedNumber value={m.xirr_pct} kind="pct" />
      </Tile>
      <Tile label="Volatility" tip="How much the value bounced around — a proxy for risk.">
        {formatPct(m.annualized_volatility_pct, 2)}
      </Tile>
      <Tile label="Sharpe" tip="Return earned per unit of risk. Higher is better.">
        {m.sharpe_ratio.toFixed(2)}
      </Tile>
      <Tile label="Sortino" tip="Like Sharpe, but only counts downside risk.">
        {m.sortino_ratio.toFixed(2)}
      </Tile>
      <Tile label="Max drawdown" tip="The worst peak-to-trough drop along the way.">
        <span className="text-down">−{m.max_drawdown_pct.toFixed(2)}%</span>
      </Tile>
    </div>
  );
}

function Tile({
  label,
  tip,
  children,
}: {
  label: string;
  tip: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="eyebrow cursor-help" title={tip}>
        {label}
      </span>
      <span className="font-mono text-sm text-fg tnum">{children}</span>
    </div>
  );
}
