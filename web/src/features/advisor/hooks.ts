"use client";

import { useMutation } from "@tanstack/react-query";
import { advisorApi } from "./api";

/** Runs the AI Advisor on demand (a mutation — it's an explicit, user-triggered
 *  and comparatively slow computation; the last report stays in mutation.data).
 *
 *  The portfolio id is passed at call time rather than baked into the hook, so
 *  switching portfolios and re-running reuses the same mutation and simply
 *  replaces the report. */
export function useAdvisor() {
  return useMutation({
    mutationFn: (environmentId?: string | null) =>
      advisorApi.generate(40, environmentId),
  });
}
