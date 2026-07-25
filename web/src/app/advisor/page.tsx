"use client";

import { Panel } from "@/components/ui/Panel";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { IconWindow } from "@/components/ui/icons";
import { ApiError } from "@/api/client";
import { useAdvisor } from "@/features/advisor/hooks";
import { AdvisorReport } from "@/features/advisor/components/AdvisorReport";

export default function AdvisorPage() {
  const advisor = useAdvisor();

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
        <div>
          <Button
            type="button"
            variant="primary"
            loading={advisor.isPending}
            onClick={() => advisor.mutate()}
          >
            {advisor.data ? "Regenerate advice" : "Generate advice"}
          </Button>
        </div>

        {advisor.isPending ? (
          <LoadingReport />
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

function LoadingReport() {
  return (
    <div className="flex flex-col gap-4">
      <Panel label="Advisor readout">
        <Skeleton className="h-20 w-full" />
      </Panel>
      <Panel label="Sector impact">
        <Skeleton className="h-24 w-full" />
      </Panel>
    </div>
  );
}
