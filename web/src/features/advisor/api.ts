import { api } from "@/api/client";
import type { AdvisorReportView } from "@/api/types";

/** The multi-agent AI Advisor: analyzes recent events and returns short/long-term
 *  guidance plus a plain-English readout. Runs local models, so it can be slow.
 *
 *  Passing an `environmentId` switches on the portfolio pass: the agent graph
 *  routes through an extra Portfolio agent that maps the market-wide calls onto
 *  the positions that portfolio actually holds. Leave it out for market-wide
 *  advice — that path is unchanged. */
export const advisorApi = {
  generate: (maxEvents = 40, environmentId?: string | null) =>
    api.post<AdvisorReportView>("/api/v1/advisor/summary", {
      max_events: maxEvents,
      environment_id: environmentId ?? null,
    }),
};
