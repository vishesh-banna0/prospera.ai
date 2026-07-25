"use client";

import { Panel } from "@/components/ui/Panel";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { formatRatioPct } from "@/lib/money";
import type {
  AdvisorReportView,
  RecommendationView,
  SectorImpactView,
} from "@/api/types";

const impactTone: Record<string, BadgeTone> = {
  positive: "up",
  negative: "down",
  mixed: "hold",
  neutral: "neutral",
};

const actionTone: Record<string, BadgeTone> = {
  buy: "up",
  sell: "down",
  avoid: "warn",
  hold: "hold",
};

const sourceTone: Record<string, BadgeTone> = {
  llm: "up",
  mixed: "hold",
  deterministic: "neutral",
  none: "neutral",
};

export function AdvisorReport({ r }: { r: AdvisorReportView }) {
  const models = r.models ?? {};
  const modelLine = Object.entries(models)
    .map(([role, m]) => `${role}: ${m}`)
    .join("  ·  ");

  return (
    <div className="flex flex-col gap-4">
      <Panel
        label="Advisor readout"
        aside={
          <Badge tone={sourceTone[r.source] ?? "neutral"} withTick={false}>
            {r.source === "llm" ? "AI agents" : r.source}
          </Badge>
        }
      >
        <p className="whitespace-pre-line text-sm leading-relaxed text-fg">{r.narrative}</p>
        <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-2xs text-fg-mute">
          <span>{r.event_count} events analyzed</span>
          {modelLine && <span aria-hidden>·</span>}
          {modelLine && <span>{modelLine}</span>}
        </div>
      </Panel>

      {r.sectors.length > 0 && (
        <Panel label="Sector impact">
          <p className="mb-2.5 text-2xs text-fg-mute">
            Effect on each sector&rsquo;s shares (the outlook), not the mood of the news
            — e.g. a war lifts Energy even though the headline is negative.
          </p>
          <div className="flex flex-col gap-2.5">
            {r.sectors.map((s) => (
              <SectorRow key={s.sector} s={s} />
            ))}
          </div>
        </Panel>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <RecommendationList
          label="Short-term · event-driven"
          recs={r.short_term}
          empty="No short-term calls from the recent events."
        />
        <RecommendationList
          label="Long-term · recovery & quality"
          recs={r.long_term}
          empty="No long-term calls from the recent events."
        />
      </div>

      <p className="font-mono text-2xs text-fg-mute">Simulated guidance — not investment advice.</p>
    </div>
  );
}

function SectorRow({ s }: { s: SectorImpactView }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm text-fg">{s.sector}</span>
          <span className="font-mono text-2xs uppercase tracking-wider text-fg-mute">
            {s.magnitude}
          </span>
        </div>
        {(s.drivers?.length ?? 0) > 0 && (
          <p className="mt-0.5 truncate text-2xs text-fg-dim">{s.drivers?.join("  ·  ")}</p>
        )}
      </div>
      <Badge tone={impactTone[s.impact] ?? "neutral"}>{s.impact}</Badge>
    </div>
  );
}

function RecommendationList({
  label,
  recs,
  empty,
}: {
  label: string;
  recs: readonly RecommendationView[];
  empty: string;
}) {
  return (
    <Panel label={label}>
      {recs.length === 0 ? (
        <p className="text-2xs text-fg-mute">{empty}</p>
      ) : (
        <div className="flex flex-col gap-3">
          {recs.map((r, i) => (
            <div key={`${r.target}-${i}`} className="flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <Badge tone={actionTone[r.action] ?? "neutral"}>{r.action}</Badge>
                <span className="font-mono text-sm text-fg">{r.target}</span>
                <span className="ml-auto font-mono text-2xs text-fg-mute tnum">
                  {formatRatioPct(r.confidence)}
                </span>
              </div>
              {r.rationale && <p className="text-2xs leading-relaxed text-fg-dim">{r.rationale}</p>}
              {r.trigger && (
                <p className="text-2xs text-fg-mute">
                  <span className="uppercase tracking-wider">exit:</span> {r.trigger}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}
