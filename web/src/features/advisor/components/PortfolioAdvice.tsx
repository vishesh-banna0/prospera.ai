"use client";

import { Panel } from "@/components/ui/Panel";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { formatPct, formatRatioPct } from "@/lib/money";
import type { HoldingActionView, PortfolioAdviceView } from "@/api/types";

/**
 * What the market view means for the positions you actually own.
 *
 * The rest of the advisor talks about the market. This panel is the answer to
 * "so what do I do?" — one action per holding, including the ones nothing has
 * happened to. Those come back as "hold" on purpose: a position no recent event
 * touches is a position to leave alone, and saying so explicitly is more useful
 * than quietly omitting it.
 */

const actionTone: Record<string, BadgeTone> = {
  add: "up",
  trim: "warn",
  exit: "down",
  hold: "hold",
};

/** Actions that need you to do something sort above the ones that don't. */
const actionOrder: Record<string, number> = { exit: 0, trim: 1, add: 2, hold: 3 };

export function PortfolioAdvice({ p }: { p: PortfolioAdviceView }) {
  const actions = [...(p.actions ?? [])].sort(
    (a, b) => (actionOrder[a.action] ?? 9) - (actionOrder[b.action] ?? 9),
  );
  const toDo = actions.filter((a) => a.action !== "hold");

  return (
    <Panel
      label="Your portfolio"
      aside={
        <span className="font-mono text-2xs text-fg-mute">
          {p.holdings_count} position{p.holdings_count === 1 ? "" : "s"}
        </span>
      }
    >
      {p.summary && (
        <p className="mb-3 text-sm leading-relaxed text-fg">{p.summary}</p>
      )}

      {(p.concentration_warnings?.length ?? 0) > 0 && (
        <ul className="mb-3 flex flex-col gap-1.5">
          {p.concentration_warnings?.map((w) => (
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

      {actions.length === 0 ? (
        <p className="text-2xs text-fg-mute">
          No positions to advise on — this portfolio is empty.
        </p>
      ) : (
        <>
          {toDo.length === 0 && (
            <p className="mb-3 text-2xs text-fg-dim">
              Nothing in the recent news calls for a change. Every position below
              is a hold.
            </p>
          )}
          <div className="flex flex-col divide-y divide-line">
            {actions.map((a) => (
              <ActionRow key={a.symbol} a={a} />
            ))}
          </div>
        </>
      )}

      {(p.unheld_opportunities?.length ?? 0) > 0 && (
        <div className="mt-4 border-t border-line pt-3">
          <h3 className="eyebrow mb-2">Not held — worth a look</h3>
          <ul className="flex flex-col gap-1.5">
            {p.unheld_opportunities?.map((o) => (
              <li key={o} className="text-2xs leading-relaxed text-fg-dim">
                — {o}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Panel>
  );
}

function ActionRow({ a }: { a: HoldingActionView }) {
  return (
    <div className="flex flex-col gap-1 py-2.5 first:pt-0 last:pb-0">
      <div className="flex items-center gap-2">
        <Badge tone={actionTone[a.action] ?? "neutral"}>{a.action}</Badge>
        <span className="font-mono text-sm text-fg">{a.symbol}</span>
        <span className="font-mono text-2xs text-fg-mute tnum">
          {formatPct(a.weight_pct, 1)} of portfolio
        </span>
        <span className="ml-auto font-mono text-2xs text-fg-mute tnum">
          {formatRatioPct(a.confidence)}
        </span>
      </div>
      {a.rationale && (
        <p className="text-2xs leading-relaxed text-fg-dim">{a.rationale}</p>
      )}
    </div>
  );
}
