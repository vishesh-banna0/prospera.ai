"use client";

import { Panel } from "@/components/ui/Panel";
import { DataTable, type Column } from "@/components/ui/Table";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { IconGaugeEmpty } from "@/components/ui/icons";
import { cn } from "@/lib/cn";
import { formatPct } from "@/lib/money";
import { ApiError } from "@/api/client";
import type { AllocationView, CorrelationRowView } from "@/api/types";
import { useHoldings } from "../hooks";
import { usePortfolioRisk } from "../optimizerHooks";

const LOOKBACK_DAYS = 365;

/**
 * Risk of the portfolio you actually hold, right now — no suggestions.
 *
 * The per-stock numbers elsewhere in the app can't answer this: risk depends on
 * how holdings move *together*. Three stocks that all fall at the same time are
 * much riskier than three that don't, and only a portfolio-level view sees it.
 */
export function RiskPanel({ id }: { id: string }) {
  const holdings = useHoldings(id);
  const enabled = (holdings.data?.length ?? 0) >= 1;
  const q = usePortfolioRisk(id, LOOKBACK_DAYS, enabled);

  return (
    <Panel label="Risk analysis">
      {holdings.isLoading ? (
        <Skeleton className="h-32 w-full" />
      ) : !enabled ? (
        <EmptyState icon={<IconGaugeEmpty />} title="Nothing to analyze yet">
          Buy a stock and this panel will show how much risk each position adds
          to the portfolio as a whole.
        </EmptyState>
      ) : q.isLoading ? (
        <Skeleton className="h-32 w-full" />
      ) : q.isError ? (
        <ErrorState detail={(q.error as ApiError).message} onRetry={() => q.refetch()} />
      ) : q.data ? (
        <div className="flex flex-col gap-5">
          {q.data.concentration_warnings.length > 0 && (
            <ul className="flex flex-col gap-1.5">
              {q.data.concentration_warnings.map((w) => (
                <li
                  key={w}
                  className="flex items-start gap-2 rounded border border-warn/40 bg-warn/5 px-2.5 py-2 text-2xs leading-relaxed text-fg"
                >
                  <span className="font-mono text-warn">!</span>
                  <span>{w}</span>
                </li>
              ))}
            </ul>
          )}

          <div className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3 lg:grid-cols-6">
            <Tile
              label="Volatility"
              tip="How much this portfolio's value swings over a year."
              value={formatPct(q.data.metrics.volatility_pct, 1)}
            />
            <Tile
              label="Expected return"
              tip="Annual return implied by the last year of prices. An estimate, not a promise."
              value={formatPct(q.data.metrics.expected_return_pct, 1)}
            />
            <Tile
              label="Sharpe"
              tip="Return earned per unit of risk. Higher is better."
              value={q.data.metrics.sharpe_ratio.toFixed(2)}
            />
            <Tile
              label="Diversification"
              tip="1.0 means your holdings move together, so owning several is like owning one."
              value={q.data.metrics.diversification_ratio.toFixed(2)}
            />
            <Tile
              label="Effective holdings"
              tip="How many positions this behaves like, after accounting for size. Compare it to how many you actually own."
              value={`${q.data.metrics.effective_number_of_assets.toFixed(1)} of ${q.data.symbols.length}`}
            />
            <Tile
              label="Worst drop"
              tip="The deepest peak-to-trough fall this mix would have had over the window."
              value={formatPct(q.data.metrics.max_drawdown_pct, 1)}
            />
          </div>

          <div>
            <h3 className="eyebrow mb-2">Where the risk sits</h3>
            <DataTable
              columns={riskColumns}
              rows={q.data.allocations}
              getRowKey={(a) => a.symbol}
              minWidth="32rem"
            />
            <p className="mt-2 text-2xs text-fg-dim">
              If a stock&apos;s risk share is well above its weight, it is
              driving more of your outcome than its size suggests.
            </p>
          </div>

          {q.data.correlations.length > 1 && (
            <CorrelationGrid rows={q.data.correlations} />
          )}
        </div>
      ) : null}
    </Panel>
  );
}

const riskColumns: Column<AllocationView>[] = [
  { header: "Symbol", cell: (a) => <span className="text-fg">{a.symbol}</span> },
  {
    header: "Weight",
    align: "right",
    cell: (a) => formatPct(a.current_weight_pct ?? a.target_weight_pct, 1),
  },
  {
    header: "Risk share",
    align: "right",
    cell: (a) => <span className="text-fg">{formatPct(a.risk_contribution_pct, 1)}</span>,
  },
  {
    header: "Volatility",
    align: "right",
    cell: (a) => formatPct(a.annualized_volatility_pct, 1),
  },
];

/**
 * How each pair of holdings moves together, from −1 (opposite) to +1 (locked
 * together). Rendered as shaded cells rather than a chart: at this size the
 * grid IS the visualization, and the numbers stay readable.
 */
function CorrelationGrid({ rows }: { rows: CorrelationRowView[] }) {
  return (
    <div>
      <h3 className="eyebrow mb-2">How they move together</h3>
      <div className="overflow-x-auto">
        <table className="border-separate border-spacing-0.5 font-mono text-[0.625rem] tnum">
          <thead>
            <tr>
              <th className="px-1 py-0.5" />
              {rows.map((r) => (
                <th
                  key={r.symbol}
                  className="px-1 py-0.5 text-right font-normal text-fg-mute"
                >
                  {short(r.symbol)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.symbol}>
                <th className="whitespace-nowrap px-1 py-0.5 text-right font-normal text-fg-mute">
                  {short(row.symbol)}
                </th>
                {row.correlations.map((value, i) => (
                  <td
                    key={`${row.symbol}-${rows[i]?.symbol ?? i}`}
                    title={`${row.symbol} vs ${rows[i]?.symbol ?? ""}: ${value.toFixed(2)}`}
                    className={cn(
                      "px-1.5 py-0.5 text-right text-fg",
                      // Only the genuinely high correlations get emphasis —
                      // those are the ones that quietly undo diversification.
                      value >= 0.7 && row.symbol !== rows[i]?.symbol
                        ? "bg-warn/15"
                        : value <= 0
                          ? "bg-panel-2 text-fg-dim"
                          : "bg-panel-2",
                    )}
                  >
                    {value.toFixed(2)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-2xs text-fg-dim">
        1.00 means the two move in lockstep; 0 means unrelated; below 0 means
        they tend to move opposite ways. Highlighted pairs are the ones that
        barely diversify each other.
      </p>
    </div>
  );
}

/** Ticker without its exchange suffix, so the grid headers stay narrow. */
function short(symbol: string): string {
  return symbol.replace(/\.(NS|BO|MF)$/i, "");
}

function Tile({
  label,
  tip,
  value,
}: {
  label: string;
  tip: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="eyebrow cursor-help" title={tip}>
        {label}
      </span>
      <span className="font-mono text-sm text-fg tnum">{value}</span>
    </div>
  );
}
