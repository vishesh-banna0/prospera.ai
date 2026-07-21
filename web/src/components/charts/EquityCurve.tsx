"use client";

import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatCompactINR, formatINR, formatSignedINR } from "@/lib/money";

/**
 * The backtest's load-bearing visual. Two series — what you put in (invested)
 * and what it became (value) — and the widening gap between them IS the story.
 * So `value` is the emphasized line with a flat translucent fill, and `invested`
 * is a quiet dashed baseline. The fill color is the market's verdict: green when
 * value ended above invested, red when below.
 *
 * Recharts (not a hand-rolled SVG) because it handles responsive sizing, axes,
 * and hit-testing for the tooltip — the boring, maintainable choice. The gauge
 * is hand-built; a value-over-time line is exactly what Recharts is for.
 */

export interface EquityPoint {
  on: string;
  invested: number;
  value: number;
}

const dateFmt = new Intl.DateTimeFormat("en-IN", { month: "short", year: "2-digit" });

function fmtAxisDate(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : dateFmt.format(d);
}

export function EquityCurve({ data, height = 260 }: { data: EquityPoint[]; height?: number }) {
  const last = data[data.length - 1];
  const inProfit = last ? last.value >= last.invested : true;
  const valueColor = inProfit ? "rgb(var(--up))" : "rgb(var(--down))";

  return (
    <div style={{ height }} className="w-full font-mono">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
          <CartesianGrid stroke="rgb(var(--line))" vertical={false} />
          <XAxis
            dataKey="on"
            tickFormatter={fmtAxisDate}
            tick={{ fill: "rgb(var(--fg-mute))", fontSize: 10 }}
            stroke="rgb(var(--line-2))"
            tickLine={false}
            minTickGap={40}
          />
          <YAxis
            tickFormatter={(v) => formatCompactINR(v)}
            tick={{ fill: "rgb(var(--fg-mute))", fontSize: 10 }}
            stroke="rgb(var(--line-2))"
            tickLine={false}
            width={64}
          />
          <Tooltip content={<CurveTooltip />} cursor={{ stroke: "rgb(var(--line-2))" }} />
          <Area
            type="monotone"
            dataKey="value"
            stroke={valueColor}
            strokeWidth={1.75}
            fill={valueColor}
            fillOpacity={0.1}
            isAnimationActive={false}
            dot={false}
            name="Value"
          />
          <Line
            type="monotone"
            dataKey="invested"
            stroke="rgb(var(--fg-mute))"
            strokeWidth={1.25}
            strokeDasharray="3 3"
            isAnimationActive={false}
            dot={false}
            name="Invested"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

interface TooltipEntry {
  value: number;
  payload: EquityPoint;
}

function CurveTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: TooltipEntry[];
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0]?.payload;
  if (!point) return null;
  const gap = point.value - point.invested;

  return (
    <div className="rounded border border-line-2 bg-panel px-2.5 py-2 text-2xs shadow-lg">
      <div className="mb-1 font-mono uppercase tracking-wider text-fg-mute">
        {new Date(point.on).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })}
      </div>
      <Row label="Value" value={formatINR(point.value, 0)} className="text-fg" />
      <Row label="Invested" value={formatINR(point.invested, 0)} className="text-fg-dim" />
      <Row
        label="Gap"
        value={formatSignedINR(gap, 0)}
        className={gap >= 0 ? "text-up" : "text-down"}
      />
    </div>
  );
}

function Row({ label, value, className }: { label: string; value: string; className: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4 font-mono tnum">
      <span className="text-fg-mute">{label}</span>
      <span className={className}>{value}</span>
    </div>
  );
}
