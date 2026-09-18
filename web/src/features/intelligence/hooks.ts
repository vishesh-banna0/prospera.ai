"use client";

import { useQuery } from "@tanstack/react-query";
import { intelApi } from "./api";

/**
 * Overview rankings across every analyzed symbol. All keyed under
 * ["intel-overview", …] so a fresh Analyze run (which invalidates that prefix)
 * refreshes the lists automatically.
 */
export function useCompanyScores() {
  return useQuery({
    queryKey: ["intel-overview", "company"],
    queryFn: intelApi.companyScores,
    staleTime: 30_000,
  });
}

export function usePredictions() {
  return useQuery({
    queryKey: ["intel-overview", "predictions"],
    queryFn: intelApi.predictions,
    staleTime: 30_000,
  });
}

export function useSignals() {
  return useQuery({
    queryKey: ["intel-overview", "signals"],
    queryFn: intelApi.signals,
    staleTime: 30_000,
  });
}

/**
 * The multi-horizon forecast for one symbol.
 *
 * A query, not a mutation: it only reads and computes, so revisiting the symbol
 * should hit the cache. `includeEvents` is part of the key, so toggling the
 * news tilt off fetches the price-only version once and then keeps both.
 */
export function useForecast(symbol: string, includeEvents: boolean) {
  return useQuery({
    queryKey: ["forecast", symbol, includeEvents],
    queryFn: () => intelApi.forecast(symbol, includeEvents),
    enabled: !!symbol,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}

export function useOpinions() {
  return useQuery({
    queryKey: ["intel-overview", "opinions"],
    queryFn: intelApi.opinions,
    staleTime: 30_000,
  });
}
