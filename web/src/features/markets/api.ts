import { api } from "@/api/client";
import type {
  CompanyProfileView,
  HistoricalPriceSeriesView,
  InstrumentSearchResultsView,
  QuoteView,
} from "@/api/types";

/**
 * Market-data endpoints. Quote and search are Finnhub-backed; history and profile
 * come from yfinance. All prices are already converted to INR by the backend.
 */
export const marketApi = {
  search: (query: string) =>
    api.post<InstrumentSearchResultsView>("/api/v1/market-data/search", { query }),

  quote: (symbol: string) => api.get<QuoteView>(`/api/v1/market-data/quote/${enc(symbol)}`),

  profile: (symbol: string) =>
    api.get<CompanyProfileView>(`/api/v1/market-data/profile/${enc(symbol)}`),

  /** Reads normalized history and auto-syncs any missing bars in the window. */
  history: (symbol: string, startISO: string, endISO: string) =>
    api.get<HistoricalPriceSeriesView>(
      `/api/v1/market-data/history/${enc(symbol)}?start_at=${encodeURIComponent(
        startISO,
      )}&end_at=${encodeURIComponent(endISO)}&auto_sync=true`,
    ),
};

function enc(symbol: string) {
  return encodeURIComponent(symbol.trim().toUpperCase());
}
