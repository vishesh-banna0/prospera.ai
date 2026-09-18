import { api } from "@/api/client";
import type {
  CompanyScoreView,
  CompanyScoresView,
  FusedSignalView,
  FusedSignalsView,
  MultiHorizonForecastView,
  PredictionView,
  PredictionsView,
  ReasonedOpinionView,
  ReasonedOpinionsView,
} from "@/api/types";

/**
 * The four-stage intelligence pipeline. Each POST computes AND stores a result,
 * and each stage feeds the next (§7 of the brief): company score -> prediction
 * -> fused Buy/Hold/Sell -> written reasoning. The list GETs power the overview.
 * `action` / `stance` come back lowercase; the signal `score` is bipolar (-1..1).
 */
export const intelApi = {
  // pipeline (run in order)
  analyzeCompany: (symbol: string) =>
    api.post<CompanyScoreView>(`/api/v1/company/analyze/${enc(symbol)}?lookback_days=180`),
  predict: (symbol: string) =>
    api.post<PredictionView>(
      `/api/v1/predictions/predict/${enc(symbol)}?lookback_days=365&horizon_days=5`,
    ),
  fuseSignal: (symbol: string) => api.post<FusedSignalView>(`/api/v1/signals/fuse/${enc(symbol)}`),
  reason: (symbol: string) => api.post<ReasonedOpinionView>(`/api/v1/reasoning/analyze/${enc(symbol)}`),

  /**
   * Multi-horizon hybrid forecast. Separate from `predict` above: that one
   * computes and STORES a single-horizon forecast as part of the Analyze
   * chain, while this one is a read-only look at several horizons at once and
   * persists nothing. `include_events=false` re-runs it on price data alone,
   * which is how the UI shows what the news actually contributed.
   */
  forecast: (symbol: string, includeEvents = true) =>
    api.post<MultiHorizonForecastView>(
      `/api/v1/predictions/forecast/${enc(symbol)}?lookback_days=730` +
        `&horizons=1&horizons=5&horizons=21&horizons=63` +
        `&include_events=${includeEvents}`,
    ),

  // overview rankings
  companyScores: () => api.get<CompanyScoresView>("/api/v1/company/"),
  predictions: () => api.get<PredictionsView>("/api/v1/predictions"),
  signals: () => api.get<FusedSignalsView>("/api/v1/signals"),
  opinions: () => api.get<ReasonedOpinionsView>("/api/v1/reasoning"),
};

function enc(symbol: string) {
  return encodeURIComponent(symbol.trim().toUpperCase());
}
