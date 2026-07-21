"use client";

import Link from "next/link";
import { SymbolSearch } from "@/features/markets/components/SymbolSearch";

// UI shortcuts, not data — quick ways to jump into a symbol. Mix of US and NSE.
const EXAMPLES = ["MSFT", "GOOGL", "TSLA", "RELIANCE.NS", "INFY.NS", "TCS.NS"];

export default function MarketsPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
      <p className="eyebrow">Markets</p>
      <h1 className="mt-2 font-display text-xl font-bold text-fg">Find a stock</h1>
      <p className="mt-2 max-w-prose text-sm text-fg-dim">
        Search any listed company for a live quote, price history, and profile — all
        priced in rupees.
      </p>

      <div className="mt-6">
        <SymbolSearch autoFocus />
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <span className="font-mono text-[0.625rem] uppercase tracking-wider text-fg-mute">try</span>
        {EXAMPLES.map((s) => (
          <Link
            key={s}
            href={`/markets/${encodeURIComponent(s)}`}
            className="rounded border border-line px-2 py-0.5 font-mono text-2xs text-fg-dim hover:border-line-2 hover:text-fg"
          >
            {s}
          </Link>
        ))}
      </div>
    </div>
  );
}
