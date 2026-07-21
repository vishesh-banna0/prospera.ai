"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { researchApi, type IngestInput } from "./api";

export function useResearchStats() {
  return useQuery({ queryKey: ["research-stats"], queryFn: researchApi.stats, staleTime: 30_000 });
}

export function useDocuments() {
  return useQuery({ queryKey: ["research-docs"], queryFn: researchApi.documents, staleTime: 30_000 });
}

/** Ingest a document; refresh the doc list + stats so the new one appears. */
export function useIngest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: IngestInput) => researchApi.ingest(input),
    onSuccess: () =>
      Promise.all([
        qc.invalidateQueries({ queryKey: ["research-docs"] }),
        qc.invalidateQueries({ queryKey: ["research-stats"] }),
      ]),
  });
}

/** Semantic search is an explicit action, so it's a mutation; data holds results. */
export function useResearchSearch() {
  return useMutation({
    mutationFn: (vars: { query: string; topK: number; symbol?: string }) =>
      researchApi.search(vars.query, vars.topK, vars.symbol),
  });
}
