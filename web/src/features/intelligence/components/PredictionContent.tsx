"use client";

import { Gauge } from "@/components/ui/Gauge";
import { Badge, toneForVerdict } from "@/components/ui/Badge";
import { SignedNumber } from "@/components/ui/SignedNumber";
import type { PredictionView } from "@/api/types";

/** Next-move forecast: a direction, a probability, an expected return, and how
 *  confident the model is — plus the features that drove it (transparency). */
export function PredictionContent({ data }: { data: PredictionView }) {
  const upTone = data.direction.toLowerCase() === "up" ? "up" : "down";

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Badge tone={toneForVerdict(data.direction)}>{data.direction}</Badge>
          <span className="font-mono text-2xs text-fg-mute">over {data.horizon_days}d</span>
        </div>
        <span className="text-sm">
          <SignedNumber value={data.expected_return_pct} kind="pct" />
        </span>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Gauge
          value={data.probability_up}
          min={0}
          max={1}
          tone={upTone}
          readout={data.probability_up.toFixed(2)}
          label="P(up)"
          caption={["0.0", "1.0"]}
          majorTicks={2}
          ariaLabel={`Probability of an up move ${data.probability_up.toFixed(2)}`}
        />
        <Gauge
          value={data.confidence}
          min={0}
          max={1}
          tone="hold"
          readout={data.confidence.toFixed(2)}
          label="Confidence"
          caption={["low", "high"]}
          majorTicks={2}
          ariaLabel={`Model confidence ${data.confidence.toFixed(2)}`}
        />
      </div>

      <div className="flex flex-col gap-1.5 border-t border-line pt-3">
        <span className="eyebrow">Model inputs · {data.model_name}</span>
        <div className="flex flex-wrap gap-1.5">
          {Object.entries(data.features ?? {}).map(([k, v]) => (
            <span
              key={k}
              className="rounded-sm border border-line px-1.5 py-0.5 font-mono text-[0.625rem] text-fg-dim tnum"
            >
              {k} {v >= 0 ? "+" : ""}
              {v.toFixed(3)}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
