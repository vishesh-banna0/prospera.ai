"use client";

import { Gauge } from "@/components/ui/Gauge";
import { cn } from "@/lib/cn";
import { toneForVerdict, type BadgeTone } from "@/components/ui/Badge";
import { formatPct } from "@/lib/money";
import type { FusedSignalView, SignalComponentView } from "@/api/types";

const glyph: Record<BadgeTone, string> = {
  up: "▲",
  down: "▼",
  hold: "■",
  neutral: "•",
  warn: "!",
};
const textTone: Record<BadgeTone, string> = {
  up: "text-up",
  down: "text-down",
  hold: "text-hold",
  neutral: "text-fg-dim",
  warn: "text-warn",
};

/** The blended Buy/Hold/Sell verdict — the point where news + company + prediction
 *  become one decision. The action is the headline; the score gauge is bipolar. */
export function SignalContent({ data }: { data: FusedSignalView }) {
  const tone = toneForVerdict(data.action);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className={cn("flex items-center gap-2", textTone[tone])}>
          <span aria-hidden className="text-sm">{glyph[tone]}</span>
          <span className="font-display text-2xl font-bold uppercase tracking-wide">
            {data.action}
          </span>
        </div>
        <div className="w-full max-w-[16rem]">
          <Gauge
            value={data.score}
            min={-1}
            max={1}
            tone={tone === "up" ? "up" : tone === "down" ? "down" : "hold"}
            readout={data.score.toFixed(2)}
            label="Signal"
            caption={["sell −1", "+1 buy"]}
            majorTicks={4}
            ariaLabel={`Fused signal score ${data.score.toFixed(2)} on a scale of minus one to one`}
          />
        </div>
      </div>

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
          ariaLabel={`Signal confidence ${data.confidence.toFixed(2)}`}
        />
      </div>

      {data.components && data.components.length > 0 && (
        <div className="flex flex-col gap-2 border-t border-line pt-3">
          <span className="eyebrow">Blended from</span>
          {data.components.map((c) => (
            <Component key={c.name} c={c} />
          ))}
        </div>
      )}

      <p className="border-t border-line pt-2 font-mono text-[0.625rem] uppercase tracking-wider text-fg-mute">
        Simulated — not investment advice
      </p>
    </div>
  );
}

function Component({ c }: { c: SignalComponentView }) {
  const sign = c.score > 0 ? "up" : c.score < 0 ? "down" : "flat";
  const cls = sign === "up" ? "text-up" : sign === "down" ? "text-down" : "text-fg-dim";
  return (
    <div className={cn("flex items-center gap-3 text-2xs", !c.present && "opacity-50")}>
      <span className="w-20 shrink-0 font-mono uppercase tracking-wider text-fg-dim">{c.name}</span>
      <span className="w-12 shrink-0 font-mono text-fg-mute tnum">{formatPct(c.weight * 100, 0)}</span>
      <span className={cn("w-14 shrink-0 font-mono tnum", cls)}>
        {c.score >= 0 ? "+" : "−"}
        {Math.abs(c.score).toFixed(2)}
      </span>
      <span className="min-w-0 flex-1 truncate text-fg-mute">{c.present ? c.detail : "no data"}</span>
    </div>
  );
}
