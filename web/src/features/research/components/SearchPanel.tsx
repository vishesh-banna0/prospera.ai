"use client";

import { useState } from "react";
import { Panel } from "@/components/ui/Panel";
import { Button } from "@/components/ui/Button";
import { Input, Field } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { Skeleton } from "@/components/ui/Skeleton";
import { IconWindow } from "@/components/ui/icons";
import { ApiError } from "@/api/client";
import type { RetrievedChunkView } from "@/api/types";
import { useResearchSearch } from "../hooks";

/** Semantic search over ingested documents. Each hit shows its relevance score
 *  as a small bar — the RAG signal made visible. */
export function SearchPanel() {
  const [query, setQuery] = useState("");
  const [symbol, setSymbol] = useState("");
  const search = useResearchSearch();

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    search.mutate({ query: query.trim(), topK: 6, symbol: symbol || undefined });
  }

  const results = search.data?.results ?? [];

  return (
    <Panel label="Semantic search">
      <form onSubmit={submit} className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <Field label="Ask the documents" htmlFor="rs-query" className="flex-1">
          <Input
            id="rs-query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. margin outlook and pricing power"
          />
        </Field>
        <div className="flex items-end gap-2">
          <Field label="Symbol" htmlFor="rs-symbol">
            <Input
              id="rs-symbol"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              placeholder="any"
              className="w-24 font-mono uppercase"
            />
          </Field>
          <Button type="submit" variant="primary" loading={search.isPending} disabled={!query.trim()}>
            Search
          </Button>
        </div>
      </form>

      <div className="mt-4">
        {search.isPending ? (
          <div className="flex flex-col gap-2">
            {Array.from({ length: 3 }, (_, i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        ) : search.isError ? (
          <ErrorState detail={(search.error as ApiError).message} />
        ) : search.data ? (
          results.length === 0 ? (
            <EmptyState icon={<IconWindow />} title="No matches">
              Nothing in the ingested documents matched. Try different words, or add a
              document below.
            </EmptyState>
          ) : (
            <div className="flex flex-col gap-2">
              {results.map((r) => (
                <ResultRow key={r.chunk_id} r={r} />
              ))}
            </div>
          )
        ) : (
          <p className="text-2xs text-fg-mute">
            Ask a question and the closest passages from your documents come back,
            ranked by relevance.
          </p>
        )}
      </div>
    </Panel>
  );
}

function ResultRow({ r }: { r: RetrievedChunkView }) {
  const pct = Math.max(0, Math.min(1, r.score));
  return (
    <div className="rounded border border-line bg-panel-2/40 p-3">
      <div className="mb-1.5 flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-fg">{r.document_title}</span>
        <Badge tone="neutral" withTick={false}>{r.document_type}</Badge>
        <span className="font-mono text-[0.625rem] text-fg-mute">#{r.chunk_index}</span>
        <span className="ml-auto flex items-center gap-2">
          <span className="h-1 w-16 overflow-hidden rounded-full bg-line">
            <span className="block h-full bg-fg-dim" style={{ width: `${pct * 100}%` }} />
          </span>
          <span className="font-mono text-[0.625rem] text-fg-dim tnum">{r.score.toFixed(3)}</span>
        </span>
      </div>
      <p className="text-2xs leading-relaxed text-fg-dim">{r.text}</p>
    </div>
  );
}
