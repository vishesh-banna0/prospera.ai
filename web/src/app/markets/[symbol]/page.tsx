"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { SymbolSearch } from "@/features/markets/components/SymbolSearch";
import { QuotePanel } from "@/features/markets/components/QuotePanel";
import { PriceHistoryPanel } from "@/features/markets/components/PriceHistoryPanel";
import { ProfilePanel } from "@/features/markets/components/ProfilePanel";

export default function SymbolDetailPage() {
  const params = useParams<{ symbol: string }>();
  const raw = params?.symbol ?? "";
  const symbol = decodeURIComponent(Array.isArray(raw) ? (raw[0] ?? "") : raw).toUpperCase();

  if (!symbol) return null;

  return (
    <div className="mx-auto max-w-6xl px-4 py-5 sm:px-6">
      <div className="mb-4 flex flex-col gap-3 border-b border-line pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <Link href="/markets" className="eyebrow hover:text-fg-dim">
            ← Markets
          </Link>
          <h1 className="mt-1 font-mono text-2xl font-medium text-fg tnum">{symbol}</h1>
        </div>
        <div className="w-full sm:w-72">
          <SymbolSearch placeholder="Switch symbol…" />
        </div>
      </div>

      <div className="flex flex-col gap-4">
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="lg:col-span-1">
            <QuotePanel symbol={symbol} />
          </div>
          <div className="lg:col-span-2">
            <PriceHistoryPanel symbol={symbol} />
          </div>
        </div>
        <ProfilePanel symbol={symbol} />
      </div>

      <p className="mt-4 text-2xs text-fg-mute">
        Want to trade {symbol}?{" "}
        <Link href="/portfolio" className="text-fg-dim underline decoration-line-2 underline-offset-2 hover:text-fg">
          Open the Portfolio desk
        </Link>
        .
      </p>
    </div>
  );
}
