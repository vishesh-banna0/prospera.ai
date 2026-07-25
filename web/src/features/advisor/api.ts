import { api } from "@/api/client";
import type { AdvisorReportView } from "@/api/types";

/** The multi-agent AI Advisor: analyzes recent events and returns short/long-term
 *  guidance plus a plain-English readout. Runs local models, so it can be slow. */
export const advisorApi = {
  generate: (maxEvents = 40) =>
    api.post<AdvisorReportView>("/api/v1/advisor/summary", { max_events: maxEvents }),
};
