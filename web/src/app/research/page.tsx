"use client";

import { SearchPanel } from "@/features/research/components/SearchPanel";
import { IngestForm } from "@/features/research/components/IngestForm";
import { DocumentsList } from "@/features/research/components/DocumentsList";

export default function ResearchPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-5 sm:px-6">
      <header className="mb-4">
        <p className="eyebrow">Sources · Research</p>
        <h1 className="mt-1 font-display text-xl font-bold text-fg">Research workspace</h1>
        <p className="mt-1 max-w-2xl text-2xs text-fg-dim">
          Ingest documents, then ask questions in plain language — the closest
          passages come back ranked. This is the knowledge the reasoning engine
          cites. Runs fully offline.
        </p>
      </header>

      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <SearchPanel />
        <div className="flex flex-col gap-4">
          <IngestForm />
          <DocumentsList />
        </div>
      </div>
    </div>
  );
}
