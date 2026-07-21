"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { SymbolSearch } from "@/features/markets/components/SymbolSearch";
import { AnalyzeChain } from "@/features/intelligence/components/AnalyzeChain";

export default function IntelligenceSymbolPage() {
  const params = useParams<{ symbol: string }>();
  const raw = params?.symbol ?? "";
  const symbol = decodeURIComponent(Array.isArray(raw) ? (raw[0] ?? "") : raw).toUpperCase();

  if (!symbol) return null;

  return (
    <div className="mx-auto max-w-3xl px-4 py-5 sm:px-6">
      <div className="mb-5 flex flex-col gap-3 border-b border-line pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <Link href="/intelligence" className="eyebrow hover:text-fg-dim">
            ← Intelligence
          </Link>
          <h1 className="mt-1 font-mono text-2xl font-medium text-fg tnum">{symbol}</h1>
        </div>
        <div className="w-full sm:w-64">
          <SymbolSearch basePath="/intelligence" placeholder="Analyze another…" />
        </div>
      </div>

      <AnalyzeChain symbol={symbol} />

      <p className="mt-6 text-2xs text-fg-mute">
        See {symbol}&rsquo;s price and profile on{" "}
        <Link
          href={`/markets/${encodeURIComponent(symbol)}`}
          className="text-fg-dim underline decoration-line-2 underline-offset-2 hover:text-fg"
        >
          Markets
        </Link>
        .
      </p>
    </div>
  );
}
