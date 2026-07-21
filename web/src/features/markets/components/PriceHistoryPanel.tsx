"use client";

import { useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Panel } from "@/components/ui/Panel";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { IconWindow } from "@/components/ui/icons";
import { cn } from "@/lib/cn";
import { formatCompactINR, formatINR, toNumber } from "@/lib/money";
import { ApiError } from "@/api/client";
import { RANGES, DEFAULT_RANGE, useHistory, type RangeKey } from "../hooks";

interface Point {
  t: string;
  close: number;
}

const dateFmt = new Intl.DateTimeFormat("en-IN", { month: "short", year: "2-digit" });
const fullDateFmt = new Intl.DateTimeFormat("en-IN", { day: "2-digit", month: "short", year: "numeric" });

export function PriceHistoryPanel({ symbol }: { symbol: string }) {
  const [range, setRange] = useState<RangeKey>(DEFAULT_RANGE);
  const q = useHistory(symbol, range);

  const points: Point[] = (q.data?.prices ?? [])
    .map((p) => ({ t: p.timestamp, close: toNumber(p.close_price) ?? NaN }))
    .filter((p) => Number.isFinite(p.close));

  const first = points[0]?.close;
  const last = points[points.length - 1]?.close;
  const up = first !== undefined && last !== undefined ? last >= first : true;
  const color = up ? "rgb(var(--up))" : "rgb(var(--down))";

  return (
    <Panel
      label="Price history"
      aside={
        <div className="flex gap-1" role="group" aria-label="Chart range">
          {RANGES.map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => setRange(r)}
              aria-pressed={r === range}
              className={cn(
                "rounded-sm px-1.5 py-0.5 font-mono text-[0.625rem] uppercase tracking-wider transition-colors",
                r === range ? "bg-panel-2 text-fg" : "text-fg-mute hover:text-fg-dim",
              )}
            >
              {r}
            </button>
          ))}
        </div>
      }
    >
      {q.isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : q.isError ? (
        <ErrorState detail={(q.error as ApiError).message} onRetry={() => q.refetch()} />
      ) : points.length === 0 ? (
        <EmptyState icon={<IconWindow />} title="No data in this window">
          There aren&rsquo;t any price bars for {symbol} over the last {range}. Try a
          wider range — history is filled on demand and may not reach this far back
          yet.
        </EmptyState>
      ) : (
        <div className="h-64 w-full font-mono">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
              <CartesianGrid stroke="rgb(var(--line))" vertical={false} />
              <XAxis
                dataKey="t"
                tickFormatter={(t) => dateFmt.format(new Date(t))}
                tick={{ fill: "rgb(var(--fg-mute))", fontSize: 10 }}
                stroke="rgb(var(--line-2))"
                tickLine={false}
                minTickGap={44}
              />
              <YAxis
                dataKey="close"
                domain={["auto", "auto"]}
                tickFormatter={(v) => formatCompactINR(v)}
                tick={{ fill: "rgb(var(--fg-mute))", fontSize: 10 }}
                stroke="rgb(var(--line-2))"
                tickLine={false}
                width={64}
              />
              <Tooltip content={<ChartTooltip />} cursor={{ stroke: "rgb(var(--line-2))" }} />
              <Area
                type="monotone"
                dataKey="close"
                stroke={color}
                strokeWidth={1.75}
                fill={color}
                fillOpacity={0.1}
                isAnimationActive={false}
                dot={false}
                name="Close"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </Panel>
  );
}

interface TooltipEntry {
  payload: Point;
}
function ChartTooltip({ active, payload }: { active?: boolean; payload?: TooltipEntry[] }) {
  if (!active || !payload?.length) return null;
  const p = payload[0]?.payload;
  if (!p) return null;
  return (
    <div className="rounded border border-line-2 bg-panel px-2.5 py-2 text-2xs">
      <div className="mb-0.5 font-mono uppercase tracking-wider text-fg-mute">
        {fullDateFmt.format(new Date(p.t))}
      </div>
      <div className="font-mono text-fg tnum">{formatINR(p.close)}</div>
    </div>
  );
}
