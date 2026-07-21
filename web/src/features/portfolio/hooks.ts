"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { portfolioApi, type OrderSide } from "./api";

/**
 * Query keys and hooks for one portfolio. All server state flows through here so
 * a trade or a deposit refreshes every affected panel automatically — no manual
 * "reload" anywhere.
 */
const keys = {
  environment: (id: string) => ["environment", id] as const,
  performance: (id: string) => ["performance", id] as const,
  holdings: (id: string) => ["holdings", id] as const,
  transactions: (id: string) => ["transactions", id] as const,
};

export function useEnvironment(id: string | null) {
  return useQuery({
    queryKey: keys.environment(id ?? "none"),
    queryFn: () => portfolioApi.getEnvironment(id as string),
    enabled: !!id,
  });
}

export function usePerformance(id: string | null) {
  return useQuery({
    queryKey: keys.performance(id ?? "none"),
    queryFn: () => portfolioApi.getPerformance(id as string),
    enabled: !!id,
  });
}

export function useHoldings(id: string | null) {
  return useQuery({
    queryKey: keys.holdings(id ?? "none"),
    queryFn: () => portfolioApi.getHoldings(id as string),
    enabled: !!id,
  });
}

export function useTransactions(id: string | null) {
  return useQuery({
    queryKey: keys.transactions(id ?? "none"),
    queryFn: () => portfolioApi.getTransactions(id as string),
    enabled: !!id,
  });
}

/** Refresh every panel that a write could have changed. */
function useRefresh(id: string) {
  const qc = useQueryClient();
  return () =>
    Promise.all([
      qc.invalidateQueries({ queryKey: keys.environment(id) }),
      qc.invalidateQueries({ queryKey: keys.performance(id) }),
      qc.invalidateQueries({ queryKey: keys.holdings(id) }),
      qc.invalidateQueries({ queryKey: keys.transactions(id) }),
    ]);
}

export function useCashMutation(id: string) {
  const refresh = useRefresh(id);
  return useMutation({
    mutationFn: (vars: { kind: "deposit" | "withdraw"; amount: number }) =>
      portfolioApi.adjustCash(id, vars.kind, vars.amount),
    onSuccess: refresh,
  });
}

export function useTradeMutation(id: string) {
  const refresh = useRefresh(id);
  return useMutation({
    mutationFn: (vars: { side: OrderSide; symbol: string; quantity: number }) =>
      portfolioApi.trade(id, vars.side, vars.symbol, vars.quantity),
    onSuccess: refresh,
  });
}

export function useCreateEnvironment() {
  return useMutation({
    mutationFn: (name: string) => portfolioApi.createEnvironment(name),
  });
}

export function useRenameEnvironment(id: string) {
  const refresh = useRefresh(id);
  return useMutation({
    mutationFn: (newName: string) => portfolioApi.renameEnvironment(id, newName),
    onSuccess: refresh,
  });
}

export function useDeleteEnvironment() {
  return useMutation({
    mutationFn: (id: string) => portfolioApi.deleteEnvironment(id),
  });
}
