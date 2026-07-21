"use client";

import { useMutation } from "@tanstack/react-query";
import { backtestApi, type BacktestInput } from "./api";

/** Runs a backtest on submit. A mutation (not a query) because it's an explicit,
 *  user-triggered computation, and we keep the last result in mutation.data. */
export function useBacktest() {
  return useMutation({
    mutationFn: (input: BacktestInput) => backtestApi.run(input),
  });
}
