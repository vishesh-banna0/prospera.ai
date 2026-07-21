"use client";

import { Gauge, type GaugeTone } from "@/components/ui/Gauge";
import { Badge, toneForVerdict } from "@/components/ui/Badge";
import { formatCompactINR } from "@/lib/money";
import type { CompanyScoreView } from "@/api/types";

/** Company intelligence: an overall 0–100 score with growth/risk/sentiment sub-
 *  scores, each drawn as the same calibrated gauge. */
export function CompanyScoreContent({ data }: { data: CompanyScoreView }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-[16rem] flex-1">
          <Gauge
            value={data.overall_score}
            min={0}
            max={100}
            tone={scoreTone(data.overall_score)}
            readout={data.overall_score.toFixed(0)}
            label="Overall"
            caption={["0", "100"]}
            ariaLabel={`Overall company score ${data.overall_score.toFixed(0)} of 100`}
          />
        </div>
        <Badge tone={toneForVerdict(data.rating)}>{data.rating}</Badge>
      </div>

      <div className="grid gap-4 border-t border-line pt-3 sm:grid-cols-3">
        <SubScore label="Growth" value={data.growth_score} />
        <SubScore label="Risk" value={data.risk_score} />
        <SubScore label="Sentiment" value={data.sentiment_score} />
      </div>

      <div className="flex flex-wrap gap-x-6 gap-y-1 font-mono text-2xs text-fg-mute">
        {data.sector && <span>{data.sector}</span>}
        {data.market_cap && <span>mkt cap {formatCompactINR(data.market_cap)}</span>}
        <span>{data.price_points} sessions</span>
        <span>{data.event_count} events</span>
      </div>

      {(data.rationale ?? []).length > 0 && (
        <ul className="flex flex-col gap-1 border-t border-line pt-3">
          {(data.rationale ?? []).map((r, i) => (
            <li key={i} className="flex gap-2 text-2xs text-fg-dim">
              <span className="text-fg-mute">·</span>
              {r}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function SubScore({ label, value }: { label: string; value: number }) {
  return (
    <Gauge
      value={value}
      min={0}
      max={100}
      tone="hold"
      readout={value.toFixed(0)}
      label={label}
      majorTicks={2}
      minorPerMajor={5}
      ariaLabel={`${label} score ${value.toFixed(0)} of 100`}
    />
  );
}

function scoreTone(score: number): GaugeTone {
  if (score >= 60) return "up";
  if (score < 40) return "down";
  return "hold";
}
