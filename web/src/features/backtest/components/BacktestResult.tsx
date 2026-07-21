"use client";

import { Panel } from "@/components/ui/Panel";
import { Badge } from "@/components/ui/Badge";
import { SignedNumber } from "@/components/ui/SignedNumber";
import { EquityCurve } from "@/components/charts/EquityCurve";
import { formatINR } from "@/lib/money";
import type { BacktestResultView } from "@/api/types";
import { MetricsGrid } from "./MetricsGrid";

const dateFmt = new Intl.DateTimeFormat("en-IN", { day: "2-digit", month: "short", year: "numeric" });
function fmtDate(d: string): string {
  const dt = new Date(d);
  return Number.isNaN(dt.getTime()) ? d : dateFmt.format(dt);
}

export function BacktestResult({ r }: { r: BacktestResultView }) {
  const m = r.metrics;
  const strategyLabel = r.strategy === "sip" ? "Monthly SIP" : "Lump sum";

  return (
    <div className="flex flex-col gap-4">
      <Panel label="Result">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="neutral" withTick={false}>{strategyLabel}</Badge>
              <span className="font-mono text-sm text-fg">{r.symbol}</span>
              <span className="font-mono text-2xs text-fg-mute tnum">
                {fmtDate(r.start_date)} → {fmtDate(r.end_date)}
              </span>
            </div>
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <span className="font-mono text-2xl leading-none text-fg tnum">
                {formatINR(m.final_value, 0)}
              </span>
              <span className="text-sm">
                <SignedNumber value={m.profit} kind="inr" decimals={0} />
              </span>
              <span className="text-2xs">
                <SignedNumber value={m.total_return_pct} kind="pct" />
              </span>
            </div>
            <p className="font-mono text-2xs text-fg-mute tnum">
              invested {formatINR(m.total_invested, 0)} · {r.units.toFixed(4)} units
            </p>
          </div>
        </div>
      </Panel>

      <Panel
        label="Invested vs value"
        aside={
          <div className="flex items-center gap-4 font-mono text-2xs text-fg-mute">
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-0.5 w-4 bg-up" /> value
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-0 w-4 border-t border-dashed border-fg-mute" /> invested
            </span>
          </div>
        }
      >
        <EquityCurve data={r.curve ?? []} height={300} />
      </Panel>

      <Panel label="Metrics">
        <MetricsGrid m={m} />
      </Panel>
    </div>
  );
}
