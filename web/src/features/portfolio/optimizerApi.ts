import { api } from "@/api/client";
import type { PortfolioOptimizationView, PortfolioRiskView } from "@/api/types";

/**
 * Wrappers over the two portfolio-optimization endpoints.
 *
 * Kept separate from `api.ts` (the trading desk) because these are advisory
 * reads, not writes: nothing here changes the portfolio. The optimizer tells
 * you what it *would* do; you still place the trades yourself on the trade
 * desk. That separation is deliberate — a one-click "rebalance" button would
 * hide how much is being bought and sold.
 */

/** The four ways the optimizer can be told what "best" means. */
export type Objective =
  | "max_sharpe"
  | "min_variance"
  | "inverse_volatility"
  | "equal_weight";

/** Labels and one-line explanations, so the UI never shows a bare enum. */
export const OBJECTIVES: {
  value: Objective;
  label: string;
  blurb: string;
}[] = [
  {
    value: "max_sharpe",
    label: "Best risk-adjusted",
    blurb: "Chase the most return per unit of risk taken.",
  },
  {
    value: "min_variance",
    label: "Steadiest",
    blurb: "Make the portfolio bounce around as little as possible.",
  },
  {
    value: "inverse_volatility",
    label: "Risk parity",
    blurb: "Give calmer stocks more weight, jumpier ones less.",
  },
  {
    value: "equal_weight",
    label: "Equal split",
    blurb: "Same amount in everything — the baseline to beat.",
  },
];

export interface OptimizeParams {
  environmentId: string;
  objective: Objective;
  lookbackDays: number;
  /** Cap on any one position, as a fraction (0.35 = 35%). */
  maxWeight: number;
}

export const optimizerApi = {
  optimize: (p: OptimizeParams) =>
    api.post<PortfolioOptimizationView>("/api/v1/portfolio/optimize", {
      environment_id: p.environmentId,
      symbols: [],
      objective: p.objective,
      lookback_days: p.lookbackDays,
      max_weight: p.maxWeight,
      risk_free_rate: 0,
    }),

  risk: (environmentId: string, lookbackDays: number) =>
    api.post<PortfolioRiskView>("/api/v1/portfolio/risk", {
      environment_id: environmentId,
      lookback_days: lookbackDays,
      risk_free_rate: 0,
    }),
};
