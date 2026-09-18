"use client";

import { useState } from "react";
import { Panel } from "@/components/ui/Panel";
import { Badge, toneForVerdict } from "@/components/ui/Badge";
import { SignedNumber } from "@/components/ui/SignedNumber";
import { Skeleton } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/States";
import { cn } from "@/lib/cn";
import { ApiError } from "@/api/client";
import type { HorizonForecastView } from "@/api/types";
import { useForecast } from "../hooks";

/** Plain-English names for the horizons the backend returns. */
const HORIZON_LABELS: Record<number, string> = {
  1: "Tomorrow",
  5: "1 week",
  21: "1 month",
  63: "3 months",
};

function horizonLabel(days: number): string {
  return HORIZON_LABELS[days] ?? `${days}d`;
}

/**
 * The hybrid forecast, across several horizons at once.
 *
 * Three models vote — a classifier on technical features, an EWMA drift model,
 * and an AR(1) model on returns — and recent news nudges the result. Several
 * horizons are shown together on purpose: tomorrow's direction is close to a
 * coin flip and accuracy improves with distance, so a single number invites
 * reading far more into it than it can carry.
 */
export function ForecastPanel({ symbol }: { symbol: string }) {
  // Off = re-run on price history alone. The comparison is the honest way to
  // see how much the news term is actually doing.
  const [includeEvents, setIncludeEvents] = useState(true);
  const q = useForecast(symbol, includeEvents);

  return (
    <Panel
      label="Forecast · multi-horizon"
      aside={
        <button
          type="button"
          onClick={() => setIncludeEvents((v) => !v)}
          aria-pressed={includeEvents}
          title="Toggle whether recent news nudges the forecast"
          className={cn(
            "rounded-sm px-1.5 py-0.5 font-mono text-[0.625rem] uppercase tracking-wider transition-colors",
            includeEvents ? "bg-panel-2 text-fg" : "text-fg-mute hover:text-fg-dim",
          )}
        >
          {includeEvents ? "news on" : "news off"}
        </button>
      }
    >
      {q.isLoading ? (
        <Skeleton className="h-32 w-full" />
      ) : q.isError ? (
        <ErrorState detail={(q.error as ApiError).message} onRetry={() => q.refetch()} />
      ) : q.data ? (
        <div className="flex flex-col gap-4">
          <div className="flex flex-col divide-y divide-line">
            {q.data.forecasts.map((f) => (
              <HorizonRow key={f.horizon_days} f={f} />
            ))}
          </div>

          <div className="flex flex-col gap-1.5 border-t border-line pt-3">
            <span className="eyebrow">News tilt</span>
            {q.data.event_count > 0 ? (
              <p className="text-2xs leading-relaxed text-fg-dim">
                {q.data.event_count} recent event
                {q.data.event_count === 1 ? "" : "s"} for {q.data.symbol} scored{" "}
                <span className="font-mono text-fg tnum">
                  {q.data.event_score > 0 ? "+" : ""}
                  {q.data.event_score.toFixed(2)}
                </span>{" "}
                {describeScore(q.data.event_score)} Toggle{" "}
                <span className="text-fg">news off</span> to see the forecast on
                price history alone.
              </p>
            ) : null}
            {q.data.event_count > 0 ? (
              <p className="text-2xs leading-relaxed text-fg-mute">
                News shifts the <em>probability</em> only, not the expected
                return — sentiment is a weak hint about direction and says
                nothing reliable about the size of a move.
              </p>
            ) : (
              <p className="text-2xs leading-relaxed text-fg-dim">
                {includeEvents
                  ? "No recent events for this symbol, so the forecast is price-only. Sync news and extract events to add the news signal."
                  : "News tilt is switched off — this is the price-only forecast."}
              </p>
            )}
          </div>

          <p className="font-mono text-[0.625rem] text-fg-mute">
            {q.data.model_name} · {q.data.observations} days of history
          </p>
        </div>
      ) : null}
    </Panel>
  );
}

function describeScore(score: number): string {
  if (score > 0.15) return "(net positive), nudging the forecast up.";
  if (score < -0.15) return "(net negative), nudging the forecast down.";
  return "(roughly neutral), so it barely moves the forecast.";
}

function HorizonRow({ f }: { f: HorizonForecastView }) {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 py-2.5 first:pt-0 last:pb-0">
      <span className="w-20 shrink-0 font-mono text-2xs text-fg-mute">
        {horizonLabel(f.horizon_days)}
      </span>
      <Badge tone={toneForVerdict(f.direction)}>{f.direction}</Badge>
      <span className="text-xs">
        <SignedNumber value={f.expected_return_pct} kind="pct" decimals={2} />
      </span>

      {/* A probability bar centered on 0.5: a coin flip sits in the middle and
          reads as "no information", which is the honest default for a forecast. */}
      <span className="ml-auto flex items-center gap-2">
        <ProbabilityBar p={f.probability_up} />
        <span className="w-10 text-right font-mono text-2xs text-fg tnum">
          {f.probability_up.toFixed(2)}
        </span>
        <span
          className="w-12 text-right font-mono text-[0.625rem] text-fg-mute tnum"
          title="How confident the ensemble is, after discounting for models that lacked data"
        >
          ±{(1 - f.confidence).toFixed(2)}
        </span>
      </span>
    </div>
  );
}

function ProbabilityBar({ p }: { p: number }) {
  const clamped = Math.min(1, Math.max(0, p));
  // Distance from a coin flip, as a share of each half of the bar.
  const width = Math.abs(clamped - 0.5) * 2 * 50;
  const up = clamped >= 0.5;
  return (
    <span
      className="relative block h-1.5 w-24 rounded-sm bg-panel-2"
      aria-hidden="true"
    >
      <span className="absolute left-1/2 top-0 h-full w-px bg-line-2" />
      <span
        className={cn("absolute top-0 h-full rounded-sm", up ? "bg-up" : "bg-down")}
        style={
          up
            ? { left: "50%", width: `${width}%` }
            : { right: "50%", width: `${width}%` }
        }
      />
    </span>
  );
}
