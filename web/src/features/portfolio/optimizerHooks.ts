"use client";

import { useQuery } from "@tanstack/react-query";
import { optimizerApi, type Objective } from "./optimizerApi";

/**
 * Server state for the optimizer panels.
 *
 * Both are `useQuery` rather than `useMutation` even though the endpoints are
 * POSTs: they only read and compute, so re-running with the same settings
 * should hit the cache instead of the network. The settings are part of the
 * query key, so changing the objective refetches automatically — no submit
 * button needed.
 *
 * `enabled` gates on having at least two holdings, because the backend
 * (correctly) rejects optimizing a one-stock portfolio. Better to not ask than
 * to show the user an error they can't act on.
 */

const keys = {
  optimize: (id: string, objective: string, lookback: number, maxWeight: number) =>
    ["portfolio-optimize", id, objective, lookback, maxWeight] as const,
  risk: (id: string, lookback: number) => ["portfolio-risk", id, lookback] as const,
};

export function useOptimizedPortfolio(
  id: string,
  objective: Objective,
  lookbackDays: number,
  maxWeight: number,
  enabled: boolean,
) {
  return useQuery({
    queryKey: keys.optimize(id, objective, lookbackDays, maxWeight),
    queryFn: () =>
      optimizerApi.optimize({ environmentId: id, objective, lookbackDays, maxWeight }),
    enabled,
    // Price history barely moves within a session, and each call refits several
    // models over a year of data. Keep results for five minutes.
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}

export function usePortfolioRisk(id: string, lookbackDays: number, enabled: boolean) {
  return useQuery({
    queryKey: keys.risk(id, lookbackDays),
    queryFn: () => optimizerApi.risk(id, lookbackDays),
    enabled,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}
