"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { newsApi, type ArticleFilters } from "./api";

export function useWarehouseStats() {
  return useQuery({ queryKey: ["news-stats"], queryFn: newsApi.warehouseStats, staleTime: 60_000 });
}

export function useArticles(filters: ArticleFilters) {
  return useQuery({
    queryKey: ["news-articles", filters],
    queryFn: () => newsApi.articles(filters),
    staleTime: 30_000,
  });
}

export function useEventStats() {
  return useQuery({ queryKey: ["event-stats"], queryFn: newsApi.eventStats, staleTime: 30_000 });
}

export function useEvents(limit = 30) {
  return useQuery({ queryKey: ["events", limit], queryFn: () => newsApi.events(limit), staleTime: 30_000 });
}

/** Extract structured events from the collected articles, then refresh both. */
export function useExtractEvents() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: newsApi.extractEvents,
    onSuccess: () =>
      Promise.all([
        qc.invalidateQueries({ queryKey: ["events"] }),
        qc.invalidateQueries({ queryKey: ["event-stats"] }),
      ]),
  });
}
