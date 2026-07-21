"use client";

import { useCallback, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ApiError } from "@/api/client";
import type {
  CompanyScoreView,
  FusedSignalView,
  PredictionView,
  ReasonedOpinionView,
} from "@/api/types";
import { intelApi } from "./api";

/**
 * Orchestrates the four-stage Analyze pipeline as ONE choreographed event. Each
 * stage runs only after the previous one resolves — because each genuinely feeds
 * the next — and its status is exposed so the UI can reveal the stages in order.
 * This sequential, visible reasoning chain is the app's signature moment.
 */

export type StageStatus = "idle" | "running" | "done" | "error";

export interface StageState<T> {
  status: StageStatus;
  data: T | null;
  error: string | null;
}

export interface AnalyzeState {
  company: StageState<CompanyScoreView>;
  prediction: StageState<PredictionView>;
  signal: StageState<FusedSignalView>;
  reasoning: StageState<ReasonedOpinionView>;
}

export const STAGE_ORDER = ["company", "prediction", "signal", "reasoning"] as const;
export type StageKey = (typeof STAGE_ORDER)[number];

function idle<T>(): StageState<T> {
  return { status: "idle", data: null, error: null };
}

const initialState = (): AnalyzeState => ({
  company: idle(),
  prediction: idle(),
  signal: idle(),
  reasoning: idle(),
});

const prefersReducedMotion = () =>
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

const breath = (ms: number) =>
  new Promise((r) => setTimeout(r, prefersReducedMotion() ? 0 : ms));

export function useAnalyze(symbol: string) {
  const [state, setState] = useState<AnalyzeState>(initialState);
  const [running, setRunning] = useState(false);
  const runId = useRef(0);
  const qc = useQueryClient();

  const patch = useCallback(<K extends StageKey>(key: K, next: Partial<AnalyzeState[K]>) => {
    setState((s) => ({ ...s, [key]: { ...s[key], ...next } }));
  }, []);

  const run = useCallback(async () => {
    const myRun = ++runId.current;
    const stale = () => runId.current !== myRun;

    setRunning(true);
    setState(initialState());

    try {
      patch("company", { status: "running" });
      const company = await intelApi.analyzeCompany(symbol);
      if (stale()) return;
      patch("company", { status: "done", data: company });
      await breath(280);
      if (stale()) return;

      patch("prediction", { status: "running" });
      const prediction = await intelApi.predict(symbol);
      if (stale()) return;
      patch("prediction", { status: "done", data: prediction });
      await breath(280);
      if (stale()) return;

      patch("signal", { status: "running" });
      const signal = await intelApi.fuseSignal(symbol);
      if (stale()) return;
      patch("signal", { status: "done", data: signal });
      await breath(280);
      if (stale()) return;

      patch("reasoning", { status: "running" });
      const reasoning = await intelApi.reason(symbol);
      if (stale()) return;
      patch("reasoning", { status: "done", data: reasoning });
    } catch (e) {
      if (stale()) return;
      const msg = e instanceof ApiError ? e.message : "Analysis failed unexpectedly.";
      setState((s) => {
        const runningKey = STAGE_ORDER.find((k) => s[k].status === "running");
        if (!runningKey) return s;
        return { ...s, [runningKey]: { status: "error", data: null, error: msg } };
      });
    } finally {
      if (runId.current === myRun) {
        setRunning(false);
        qc.invalidateQueries({ queryKey: ["intel-overview"] });
      }
    }
  }, [symbol, patch, qc]);

  const reset = useCallback(() => {
    runId.current++;
    setRunning(false);
    setState(initialState());
  }, []);

  const started = STAGE_ORDER.some((k) => state[k].status !== "idle");

  return { state, running, started, run, reset };
}
