"use client";

import { Panel } from "@/components/ui/Panel";
import { Button } from "@/components/ui/Button";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { IconGaugeEmpty } from "@/components/ui/icons";
import { ApiError } from "@/api/client";
import { useEvents, useEventStats, useExtractEvents } from "../hooks";
import { EventCard } from "./EventCard";

/**
 * Structured events extracted from the news. When none exist yet, the empty
 * state invites the user to run extraction (the collected articles are the input).
 */
export function EventsSection() {
  const stats = useEventStats();
  const events = useEvents(30);
  const extract = useExtractEvents();

  const total = stats.data?.total_events ?? 0;
  const rows = events.data?.events ?? [];

  return (
    <Panel
      label="Structured events"
      aside={
        <div className="flex items-center gap-3">
          {stats.data && (
            <span className="font-mono text-[0.625rem] uppercase tracking-wider text-fg-mute tnum">
              {total} events
            </span>
          )}
          <Button size="sm" variant="secondary" loading={extract.isPending} onClick={() => extract.mutate()}>
            Extract events
          </Button>
        </div>
      }
      bodyClassName="p-0"
    >
      {extract.isError && (
        <div className="p-3">
          <ErrorState detail={(extract.error as ApiError).message} />
        </div>
      )}

      {events.isLoading ? (
        <div className="p-3">
          <TableSkeleton rows={4} />
        </div>
      ) : events.isError ? (
        <div className="p-3">
          <ErrorState detail={(events.error as ApiError).message} onRetry={() => events.refetch()} />
        </div>
      ) : rows.length === 0 ? (
        <EmptyState icon={<IconGaugeEmpty />} title="No events extracted yet" className="m-3">
          Turn the collected news into structured events — earnings, guidance,
          deals, and their sentiment. Press &ldquo;Extract events&rdquo; to run it.
        </EmptyState>
      ) : (
        <div>
          {rows.map((e) => (
            <EventCard key={e.event_id} e={e} />
          ))}
        </div>
      )}
    </Panel>
  );
}
