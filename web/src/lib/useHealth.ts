"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

interface HealthResponse {
  status?: string;
  app_name?: string;
}

/** Polls the backend `/health` for the status-strip live indicator. */
export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => api.get<HealthResponse>("/health"),
    refetchInterval: 20_000,
    retry: false,
    staleTime: 10_000,
  });
}
