"use client";

import { useMutation } from "@tanstack/react-query";
import { advisorApi } from "./api";

/** Runs the AI Advisor on demand (a mutation — it's an explicit, user-triggered
 *  and comparatively slow computation; the last report stays in mutation.data). */
export function useAdvisor() {
  return useMutation({
    mutationFn: () => advisorApi.generate(),
  });
}
