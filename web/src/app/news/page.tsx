"use client";

import { Skeleton } from "@/components/ui/Skeleton";
import { useWarehouseStats } from "@/features/news/hooks";
import { NewsFeed } from "@/features/news/components/NewsFeed";
import { EventsSection } from "@/features/news/components/EventsSection";

export default function NewsPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-5 sm:px-6">
      <header className="mb-4">
        <p className="eyebrow">Sources · News</p>
        <h1 className="mt-1 font-display text-xl font-bold text-fg">The tape</h1>
        <p className="mt-1 max-w-2xl text-2xs text-fg-dim">
          Collected market news and the structured events pulled from it — the raw
          material the intelligence layer reasons over.
        </p>
      </header>

      <StatsRow />

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <NewsFeed />
        <EventsSection />
      </div>
    </div>
  );
}

function StatsRow() {
  const q = useWarehouseStats();
  if (q.isLoading) return <Skeleton className="h-10 w-full" />;
  if (!q.data) return null;
  const s = q.data;
  const items: [string, number][] = [
    ["Total", s.total_articles],
    ["Global", s.global_articles],
    ["India", s.india_articles],
    ["Company", s.company_articles],
    ["Sector", s.sector_articles],
  ];
  return (
    <div className="flex flex-wrap gap-2">
      {items.map(([label, n]) => (
        <div
          key={label}
          className="flex items-baseline gap-2 rounded border border-line bg-panel px-3 py-1.5"
        >
          <span className="eyebrow">{label}</span>
          <span className="font-mono text-sm text-fg tnum">{n}</span>
        </div>
      ))}
    </div>
  );
}
