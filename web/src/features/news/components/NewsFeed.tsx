"use client";

import { useState } from "react";
import { Panel } from "@/components/ui/Panel";
import { Input } from "@/components/ui/Input";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { IconWindow } from "@/components/ui/icons";
import { cn } from "@/lib/cn";
import { useDebouncedValue } from "@/lib/useDebouncedValue";
import { ApiError } from "@/api/client";
import { useArticles } from "../hooks";
import { ArticleCard } from "./ArticleCard";

const CATEGORIES = [
  { key: "", label: "All" },
  { key: "global", label: "Global" },
  { key: "india", label: "India" },
  { key: "company", label: "Company" },
  { key: "sector", label: "Sector" },
] as const;

export function NewsFeed() {
  const [category, setCategory] = useState("");
  const [query, setQuery] = useState("");
  const [symbol, setSymbol] = useState("");
  const debouncedQuery = useDebouncedValue(query, 300);
  const debouncedSymbol = useDebouncedValue(symbol, 300);

  const q = useArticles({
    category: category || undefined,
    query: debouncedQuery || undefined,
    symbol: debouncedSymbol || undefined,
    limit: 30,
  });
  const articles = q.data?.articles ?? [];

  return (
    <Panel
      label="News feed"
      aside={
        q.data ? (
          <span className="font-mono text-[0.625rem] uppercase tracking-wider text-fg-mute tnum">
            {q.data.count} shown
          </span>
        ) : null
      }
      bodyClassName="p-0"
    >
      <div className="flex flex-col gap-2 border-b border-line p-3">
        <div className="flex flex-wrap gap-1.5">
          {CATEGORIES.map((c) => (
            <button
              key={c.key}
              type="button"
              onClick={() => setCategory(c.key)}
              aria-pressed={category === c.key}
              className={cn(
                "rounded border px-2 py-0.5 text-2xs transition-colors",
                category === c.key
                  ? "border-line-2 bg-panel-2 text-fg"
                  : "border-line text-fg-dim hover:border-line-2 hover:text-fg",
              )}
            >
              {c.label}
            </button>
          ))}
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search headlines…"
            aria-label="Search news"
            className="h-8"
          />
          <Input
            value={symbol}
            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
            placeholder="Symbol"
            aria-label="Filter by symbol"
            className="h-8 font-mono uppercase sm:w-32"
          />
        </div>
      </div>

      {q.isLoading ? (
        <div className="p-3">
          <TableSkeleton rows={5} />
        </div>
      ) : q.isError ? (
        <div className="p-3">
          <ErrorState detail={(q.error as ApiError).message} onRetry={() => q.refetch()} />
        </div>
      ) : articles.length === 0 ? (
        <EmptyState icon={<IconWindow />} title="No matching articles" className="m-3">
          Nothing in the warehouse matches these filters. Clear them, or sync more
          news on the backend.
        </EmptyState>
      ) : (
        <div>
          {articles.map((a) => (
            <ArticleCard key={a.article_id} a={a} />
          ))}
        </div>
      )}
    </Panel>
  );
}
