/**
 * Ergonomic aliases over the generated OpenAPI schema. Import these named types
 * instead of reaching into `components["schemas"][...]` everywhere.
 *
 * `schema.ts` is generated — never edit it by hand. When the backend changes,
 * run `npm run gen:api` and these aliases follow automatically.
 */
import type { components } from "./schema";

type S = components["schemas"];

// Auth
export type AuthTokenView = S["AuthTokenView"];
export type UserView = S["UserView"];

// Portfolio / simulator
export type EnvironmentView = S["EnvironmentView"];
export type HoldingView = S["HoldingView"];
export type TransactionView = S["TransactionView"];
export type PortfolioPerformanceView = S["PortfolioPerformanceView"];
export type SipPlanView = S["SipPlanView"];

// Market data
export type QuoteView = S["QuoteView"];
export type CompanyProfileView = S["CompanyProfileView"];
export type HistoricalPriceSeriesView = S["HistoricalPriceSeriesView"];
export type HistoricalPricePointView = S["HistoricalPricePointView"];
export type InstrumentSearchResultsView = S["InstrumentSearchResultsView"];
export type InstrumentSearchResultView = S["InstrumentSearchResultView"];

// Intelligence
export type CompanyScoreView = S["CompanyScoreView"];
export type CompanyScoresView = S["CompanyScoresView"];
export type PredictionView = S["PredictionView"];
export type PredictionsView = S["PredictionsView"];
export type FusedSignalView = S["FusedSignalView"];
export type FusedSignalsView = S["FusedSignalsView"];
export type SignalComponentView = S["SignalComponentView"];
export type ReasonedOpinionView = S["ReasonedOpinionView"];
export type ReasonedOpinionsView = S["ReasonedOpinionsView"];

// Backtesting
export type BacktestResultView = S["BacktestResultView"];
export type MetricsView = S["MetricsView"];
export type EquityPointView = S["EquityPointView"];
export type BenchmarkComparisonView = S["BenchmarkComparisonView"];

// Advisor (multi-agent)
export type AdvisorReportView = S["AdvisorReportView"];
export type SectorImpactView = S["SectorImpactView"];
export type RecommendationView = S["RecommendationView"];

// News / events
export type NewsArticleView = S["NewsArticleView"];
export type NewsArticlesView = S["NewsArticlesView"];
export type NewsWarehouseStatsView = S["NewsWarehouseStatsView"];
export type EventView = S["EventView"];
export type EventsView = S["EventsView"];
export type EventStatsView = S["EventStatsView"];

// Research
export type DocumentView = S["DocumentView"];
export type DocumentsView = S["DocumentsView"];
export type ResearchStatsView = S["ResearchStatsView"];
export type ResearchContextView = S["ResearchContextView"];
export type RetrievedChunkView = S["RetrievedChunkView"];
export type IngestDocumentView = S["IngestDocumentView"];
