import { api } from "@/api/client";
import type {
  EnvironmentView,
  HoldingView,
  PortfolioPerformanceView,
  TransactionView,
} from "@/api/types";

/**
 * Thin, typed wrappers over the portfolio endpoints. Request/response types come
 * from the generated schema (@/api/types). order_type is the backend's lowercase
 * enum ("buy" / "sell") — confirmed against the live API, not the older docs.
 */

export type OrderSide = "buy" | "sell";

interface OrderAck {
  status: string;
  symbol: string;
  quantity: number;
}
interface CashAck {
  status: string;
  amount: string;
}

export const portfolioApi = {
  createEnvironment: (name: string) =>
    api.post<EnvironmentView>("/api/v1/environments/", { name, owner_type: "user" }),

  getEnvironment: (id: string) => api.get<EnvironmentView>(`/api/v1/environments/${id}`),

  renameEnvironment: (id: string, newName: string) =>
    api.patch<EnvironmentView>(`/api/v1/environments/${id}`, {
      environment_id: id,
      new_name: newName,
    }),

  deleteEnvironment: (id: string) => api.del<void>(`/api/v1/environments/${id}`),

  getPerformance: (id: string) =>
    api.get<PortfolioPerformanceView>(`/api/v1/portfolios/${id}/performance`),

  getHoldings: (id: string) => api.get<HoldingView[]>(`/api/v1/portfolios/${id}/holdings`),

  getTransactions: (id: string) =>
    api.get<TransactionView[]>(`/api/v1/portfolios/${id}/transactions`),

  adjustCash: (id: string, kind: "deposit" | "withdraw", amount: number) =>
    api.post<CashAck>(`/api/v1/portfolios/${id}/cash/${kind}`, {
      environment_id: id,
      amount: { amount, currency: "INR" },
    }),

  trade: (id: string, side: OrderSide, symbol: string, quantity: number) =>
    api.post<OrderAck>(`/api/v1/portfolios/${id}/${side}`, {
      environment_id: id,
      symbol: symbol.trim().toUpperCase(),
      quantity,
      order_type: side,
    }),
};
