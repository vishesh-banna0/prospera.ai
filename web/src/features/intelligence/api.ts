import { api } from "@/api/client";
import type {
  CompanyScoreView,
  CompanyScoresView,
  FusedSignalView,
  FusedSignalsView,
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

  // overview rankings
  companyScores: () => api.get<CompanyScoresView>("/api/v1/company/"),
  predictions: () => api.get<PredictionsView>("/api/v1/predictions"),
  signals: () => api.get<FusedSignalsView>("/api/v1/signals"),
  opinions: () => api.get<ReasonedOpinionsView>("/api/v1/reasoning"),
};

function enc(symbol: string) {
  return encodeURIComponent(symbol.trim().toUpperCase());
}
