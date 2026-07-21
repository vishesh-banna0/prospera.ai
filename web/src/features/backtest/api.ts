import { api } from "@/api/client";
import type { BacktestResultView } from "@/api/types";

/** Backtest simulations. Both return metrics + a sampled equity curve, in INR. */

export type Strategy = "lumpsum" | "sip";

export interface BacktestInput {
  strategy: Strategy;
  symbol: string;
  /** For lumpsum this is the one-time amount; for SIP it's the monthly amount. */
  amount: number;
  startISO: string;
  endISO: string;
}

export const backtestApi = {
  run: ({ strategy, symbol, amount, startISO, endISO }: BacktestInput) => {
    const sym = symbol.trim().toUpperCase();
    if (strategy === "lumpsum") {
      return api.post<BacktestResultView>("/api/v1/backtest/lumpsum", {
        symbol: sym,
        amount,
        start_at: startISO,
        end_at: endISO,
      });
    }
    return api.post<BacktestResultView>("/api/v1/backtest/sip", {
      symbol: sym,
      monthly_amount: amount,
      start_at: startISO,
      end_at: endISO,
    });
  },
};
