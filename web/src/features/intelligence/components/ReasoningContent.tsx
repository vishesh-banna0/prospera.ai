"use client";

import { Gauge } from "@/components/ui/Gauge";
import { Badge, toneForVerdict } from "@/components/ui/Badge";
import type { ReasonedOpinionView } from "@/api/types";

/** The written opinion — a stance, a plain-language explanation, the drivers
 *  behind it, its citations, and how confident the machine is. The confidence
 *  instrument sits with the words it qualifies. */
export function ReasoningContent({ data }: { data: ReasonedOpinionView }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={toneForVerdict(data.stance)}>{data.stance}</Badge>
        <span className="font-mono text-[0.625rem] uppercase tracking-wider text-fg-mute">
          {data.source}
        </span>
      </div>

      <h3 className="font-display text-base font-semibold leading-snug text-fg">{data.headline}</h3>
      <p className="text-xs leading-relaxed text-fg-dim">{data.explanation}</p>

      <div className="max-w-[16rem]">
        <Gauge
          value={data.confidence}
          min={0}
          max={1}
          tone="hold"
          readout={data.confidence.toFixed(2)}
          label="Confidence"
          caption={["low", "high"]}
          majorTicks={2}
          ariaLabel={`Opinion confidence ${data.confidence.toFixed(2)}`}
        />
      </div>

      {(data.drivers ?? []).length > 0 && (
        <div className="flex flex-col gap-1.5 border-t border-line pt-3">
          <span className="eyebrow">Drivers</span>
          <ul className="flex flex-col gap-1">
            {(data.drivers ?? []).map((d, i) => (
              <li key={i} className="flex gap-2 text-2xs text-fg-dim">
                <span className="text-fg-mute">·</span>
                {d}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex flex-col gap-1.5 border-t border-line pt-3">
        <span className="eyebrow">Citations</span>
        {(data.citations ?? []).length > 0 ? (
          <ul className="flex flex-col gap-1">
            {(data.citations ?? []).map((c, i) => (
              <li key={i} className="text-2xs text-fg-dim">
                {c}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-2xs text-fg-mute">
            No research snippets cited — ingest documents in Research to ground future
            opinions.
          </p>
        )}
      </div>

      <p className="border-t border-line pt-2 font-mono text-[0.625rem] uppercase tracking-wider text-fg-mute">
        Simulated — not investment advice
      </p>
    </div>
  );
}
