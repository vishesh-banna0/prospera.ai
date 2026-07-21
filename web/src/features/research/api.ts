import { api } from "@/api/client";
import type {
  DocumentsView,
  IngestDocumentView,
  ResearchContextView,
  ResearchStatsView,
} from "@/api/types";

/** Research RAG: ingest documents, then semantic-search over their passages.
 *  Runs fully offline — the embedder is deterministic and needs no network. */

export interface IngestInput {
  title: string;
  content: string;
  document_type: string;
  symbols: string[];
}

export const researchApi = {
  stats: () => api.get<ResearchStatsView>("/api/v1/research/stats"),
  documents: () => api.get<DocumentsView>("/api/v1/research/documents"),

  ingest: (input: IngestInput) =>
    api.post<IngestDocumentView>("/api/v1/research/documents", input),

  search: (query: string, topK: number, symbol?: string) =>
    api.post<ResearchContextView>("/api/v1/research/search", {
      query,
      top_k: topK,
      ...(symbol?.trim() ? { symbol: symbol.trim().toUpperCase() } : {}),
    }),
};
