"use client";

import Link from "next/link";
import { SymbolSearch } from "@/features/markets/components/SymbolSearch";
import { PortfolioSnapshot } from "@/features/home/PortfolioSnapshot";
import { MachineCalls } from "@/features/home/MachineCalls";
import { LatestNews } from "@/features/home/LatestNews";

const EXAMPLES = ["AAPL", "MSFT", "RELIANCE.NS"];

/** The console. It opens on data — a portfolio snapshot, the machine's latest
 *  calls, the tape, and a way to analyze anything. */
export default function HomePage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-5 sm:px-6">
      <header className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="eyebrow">Console</p>
          <h1 className="mt-1 font-display text-xl font-bold text-fg">The desk</h1>
        </div>
        <div className="w-full sm:w-80">
          <SymbolSearch basePath="/intelligence" placeholder="Analyze a symbol…" />
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
            <span className="font-mono text-[0.625rem] uppercase tracking-wider text-fg-mute">try</span>
            {EXAMPLES.map((s) => (
              <Link
                key={s}
                href={`/intelligence/${encodeURIComponent(s)}`}
                className="rounded border border-line px-1.5 py-0.5 font-mono text-[0.625rem] text-fg-dim hover:border-line-2 hover:text-fg"
              >
                {s}
              </Link>
            ))}
          </div>
        </div>
      </header>

      <div className="flex flex-col gap-4">
        <PortfolioSnapshot />
        <div className="grid gap-4 lg:grid-cols-2">
          <MachineCalls />
          <LatestNews />
        </div>
      </div>

      <p className="mt-6 font-mono text-[0.625rem] uppercase tracking-wider text-fg-mute">
        Simulated — not investment advice
      </p>
    </div>
  );
}
