"use client";

import { useState } from "react";
import { Panel } from "@/components/ui/Panel";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { IconWindow } from "@/components/ui/icons";
import { cn } from "@/lib/cn";
import { ApiError } from "@/api/client";
import { useAdvisor } from "@/features/advisor/hooks";
import { AdvisorReport } from "@/features/advisor/components/AdvisorReport";
import { usePortfolioRegistry } from "@/features/portfolio/registry";

/** Sentinel for "advise on the market, not on a portfolio". */
const MARKET_WIDE = "market";

export default function AdvisorPage() {
  const advisor = useAdvisor();
  const registry = usePortfolioRegistry();
  const [target, setTarget] = useState<string>(MARKET_WIDE);

  const portfolios = registry.list ?? [];
  const forPortfolio = target !== MARKET_WIDE;
  const selectedName = portfolios.find((p) => p.id === target)?.name;

  return (
    <div className="mx-auto max-w-5xl px-4 py-5 sm:px-6">
      <header className="mb-4">
        <p className="eyebrow">Machine · Advisor</p>
        <h1 className="mt-1 font-display text-xl font-bold text-fg">AI Advisor</h1>
        <p className="mt-1 max-w-2xl text-2xs text-fg-dim">
          A team of local models reads the recent events, works out which sectors are
          affected, and gives short-term (event-driven, with exit triggers) and
          long-term (recovery &amp; quality) guidance. Runs on your machine, so it can
          take several seconds.
        </p>
      </header>

      <div className="flex flex-col gap-4">
        {/* Choosing a portfolio adds a fourth agent to the run, so it belongs
            next to the button that starts it — not buried in the report. */}
        {portfolios.length > 0 && (
          <Panel label="Advise on">
            <div className="flex flex-wrap gap-1.5" role="group" aria-label="Advice target">
              <TargetButton
                selected={target === MARKET_WIDE}
                onClick={() => setTarget(MARKET_WIDE)}
              >
                The market
              </TargetButton>
              {portfolios.map((p) => (
                <TargetButton
                  key={p.id}
                  selected={target === p.id}
                  onClick={() => setTarget(p.id)}
                >
                  {p.name}
                </TargetButton>
              ))}
            </div>
            <p className="mt-2.5 text-2xs text-fg-dim">
              {forPortfolio
                ? "A fourth agent will map the market view onto the positions this portfolio actually holds — add, trim, exit or hold, per position."
                : "Market-wide advice: sectors and calls, with no reference to what you own."}
            </p>
          </Panel>
        )}

        <div>
          <Button
            type="button"
            variant="primary"
            loading={advisor.isPending}
            onClick={() => advisor.mutate(forPortfolio ? target : null)}
          >
            {advisor.data ? "Regenerate advice" : "Generate advice"}
            {forPortfolio && selectedName ? ` for ${selectedName}` : ""}
          </Button>
        </div>

        {advisor.isPending ? (
          <LoadingReport withPortfolio={forPortfolio} />
        ) : advisor.isError ? (
          <ErrorState detail={(advisor.error as ApiError).message} />
        ) : advisor.data ? (
          <AdvisorReport r={advisor.data} />
        ) : (
          <EmptyState icon={<IconWindow />} title="No advice yet" className="mt-2">
            Click &ldquo;Generate advice&rdquo; and the agent team will analyze the latest
            events. If the events look stale, sync news first from the News screen.
          </EmptyState>
        )}
      </div>
    </div>
  );
}

function TargetButton({
  selected,
  onClick,
  children,
}: {
  selected: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={selected}
      className={cn(
        "rounded-sm border px-2 py-1 font-mono text-2xs transition-colors",
        selected
          ? "border-fg-mute bg-panel-2 text-fg"
          : "border-line-2 text-fg-mute hover:text-fg-dim",
      )}
    >
      {children}
    </button>
  );
}

function LoadingReport({ withPortfolio }: { withPortfolio: boolean }) {
  return (
    <div className="flex flex-col gap-4">
      <Panel label="Advisor readout">
        <Skeleton className="h-20 w-full" />
      </Panel>
      {withPortfolio && (
        <Panel label="Your portfolio">
          <Skeleton className="h-24 w-full" />
        </Panel>
      )}
      <Panel label="Sector impact">
        <Skeleton className="h-24 w-full" />
      </Panel>
    </div>
  );
}
