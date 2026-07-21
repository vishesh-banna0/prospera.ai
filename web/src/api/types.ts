/**
 * Ergonomic aliases over the generated OpenAPI schema. Import these named types
 * instead of reaching into `components["schemas"][...]` everywhere.
 *
 * `schema.ts` is generated — never edit it by hand. When the backend changes,
 * run `npm run gen:api` and these aliases follow automatically.
 */
import type { components } from "./schema";

type S = components["schemas"];

// Portfolio / simulator
export type EnvironmentView = S["EnvironmentView"];
export type HoldingView = S["HoldingView"];
export type TransactionView = S["TransactionView"];
export type PortfolioPerformanceView = S["PortfolioPerformanceView"];

// Market data
export type QuoteView = S["QuoteView"];
export type CompanyProfileView = S["CompanyProfileView"];
export type HistoricalPriceSeriesView = S["HistoricalPriceSeriesView"];
export type HistoricalPricePointView = S["HistoricalPricePointView"];
export type InstrumentSearchResultsView = S["InstrumentSearchResultsView"];
export type InstrumentSearchResultView = S["InstrumentSearchResultView"];

// Intelligence
export type CompanyScoreView = S["CompanyScoreView"];
export type PredictionView = S["PredictionView"];
export type FusedSignalView = S["FusedSignalView"];
export type SignalComponentView = S["SignalComponentView"];
export type ReasonedOpinionView = S["ReasonedOpinionView"];

// Backtesting
export type BacktestResultView = S["BacktestResultView"];
export type MetricsView = S["MetricsView"];
export type EquityPointView = S["EquityPointView"];

// News / research / events
export type NewsArticleView = S["NewsArticleView"];
export type EventView = S["EventView"];
export type DocumentView = S["DocumentView"];
export type ResearchContextView = S["ResearchContextView"];
