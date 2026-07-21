"use client";

import { useQuery } from "@tanstack/react-query";
import { marketApi } from "./api";

/** Chart range presets, computed from now. Keys double as labels. */
export const RANGES = ["6M", "1Y", "2Y", "5Y"] as const;
export type RangeKey = (typeof RANGES)[number];
export const DEFAULT_RANGE: RangeKey = "1Y";

const monthsBack: Record<RangeKey, number> = { "6M": 6, "1Y": 12, "2Y": 24, "5Y": 60 };

export function rangeWindow(range: RangeKey): { startISO: string; endISO: string } {
  const end = new Date();
  const start = new Date(end);
  start.setMonth(start.getMonth() - monthsBack[range]);
  return { startISO: start.toISOString(), endISO: end.toISOString() };
}

export function useSymbolSearch(term: string) {
  const q = term.trim();
  return useQuery({
    queryKey: ["symbol-search", q],
    queryFn: () => marketApi.search(q),
    enabled: q.length >= 1,
    staleTime: 60_000,
  });
}

export function useQuote(symbol: string) {
  return useQuery({
    queryKey: ["quote", symbol],
    queryFn: () => marketApi.quote(symbol),
    refetchInterval: 30_000,
    staleTime: 15_000,
  });
}

export function useProfile(symbol: string) {
  return useQuery({
    queryKey: ["profile", symbol],
    queryFn: () => marketApi.profile(symbol),
    staleTime: 60 * 60_000,
  });
}

export function useHistory(symbol: string, range: RangeKey) {
  return useQuery({
    queryKey: ["history", symbol, range],
    queryFn: () => {
      const { startISO, endISO } = rangeWindow(range);
      return marketApi.history(symbol, startISO, endISO);
    },
    staleTime: 5 * 60_000,
  });
}
