"use client";

import { Panel } from "@/components/ui/Panel";
import { Badge } from "@/components/ui/Badge";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { IconWindow } from "@/components/ui/icons";
import { ApiError } from "@/api/client";
import { useDocuments, useResearchStats } from "../hooks";

export function DocumentsList() {
  const q = useDocuments();
  const stats = useResearchStats();
  const docs = q.data?.documents ?? [];

  return (
    <Panel
      label="Documents"
      aside={
        stats.data ? (
          <span className="font-mono text-[0.625rem] uppercase tracking-wider text-fg-mute tnum">
            {stats.data.total_documents} docs · {stats.data.total_chunks} chunks
          </span>
        ) : null
      }
      bodyClassName={docs.length ? "p-0" : "p-3"}
    >
      {q.isLoading ? (
        <TableSkeleton rows={3} />
      ) : q.isError ? (
        <ErrorState detail={(q.error as ApiError).message} onRetry={() => q.refetch()} />
      ) : docs.length === 0 ? (
        <EmptyState icon={<IconWindow />} title="No documents yet">
          Add a document to build a searchable knowledge base that grounds the
          machine&rsquo;s opinions.
        </EmptyState>
      ) : (
        <ul>
          {docs.map((d) => (
            <li key={d.document_id} className="flex flex-wrap items-center gap-2 border-b border-line px-3 py-2 last:border-0">
              <span className="text-xs text-fg">{d.title}</span>
              <Badge tone="neutral" withTick={false}>{d.document_type}</Badge>
              <span className="font-mono text-[0.625rem] text-fg-mute tnum">{d.chunk_count} chunks</span>
              {(d.symbols ?? []).length > 0 && (
                <span className="font-mono text-[0.625rem] text-fg-dim">{(d.symbols ?? []).join(" · ")}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
