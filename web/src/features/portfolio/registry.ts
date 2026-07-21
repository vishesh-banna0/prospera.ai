"use client";

import { useCallback, useEffect, useState } from "react";

/**
 * The backend has no "list environments" endpoint (only fetch-by-id), so the
 * frontend keeps its own registry of portfolios the user has created, in
 * localStorage. See web/QUESTIONS.md #1 — if a GET /environments lands, this
 * whole file goes away.
 */

const KEY = "prospera.portfolios";

export interface PortfolioRef {
  id: string;
  name: string;
}

function read(): PortfolioRef[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as PortfolioRef[]) : [];
  } catch {
    return [];
  }
}

function write(list: PortfolioRef[]): void {
  window.localStorage.setItem(KEY, JSON.stringify(list));
}

/**
 * `list` is `null` until the component has mounted and read localStorage — that
 * distinguishes "still loading" from "genuinely empty" and avoids a hydration
 * mismatch (the server can't know what's in localStorage).
 */
export function usePortfolioRegistry() {
  const [list, setList] = useState<PortfolioRef[] | null>(null);

  useEffect(() => {
    setList(read());
  }, []);

  const add = useCallback((ref: PortfolioRef) => {
    setList((prev) => {
      const next = [ref, ...(prev ?? []).filter((p) => p.id !== ref.id)];
      write(next);
      return next;
    });
  }, []);

  const rename = useCallback((id: string, name: string) => {
    setList((prev) => {
      const next = (prev ?? []).map((p) => (p.id === id ? { ...p, name } : p));
      write(next);
      return next;
    });
  }, []);

  const remove = useCallback((id: string) => {
    setList((prev) => {
      const next = (prev ?? []).filter((p) => p.id !== id);
      write(next);
      return next;
    });
  }, []);

  return { list, add, rename, remove };
}
