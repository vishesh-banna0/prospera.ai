"use client";

import { SymbolSearch } from "@/features/markets/components/SymbolSearch";
import {
  CompanyScoresPanel,
  SignalsPanel,
  PredictionsPanel,
  OpinionsPanel,
} from "@/features/intelligence/components/RankingPanels";

export default function IntelligencePage() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-5 sm:px-6">
      <header className="mb-4">
        <p className="eyebrow">Machine · Intelligence</p>
        <h1 className="mt-1 font-display text-xl font-bold text-fg">What the machine thinks</h1>
        <p className="mt-1 max-w-2xl text-2xs text-fg-dim">
          Explainable, always-labelled machine opinion. Analyze any symbol to run the
          full chain; every stored result is ranked below.
        </p>
      </header>

      <div className="mb-6 max-w-md">
        <SymbolSearch basePath="/intelligence" placeholder="Analyze a symbol…" />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <CompanyScoresPanel />
        <SignalsPanel />
        <PredictionsPanel />
        <OpinionsPanel />
      </div>
    </div>
  );
}
