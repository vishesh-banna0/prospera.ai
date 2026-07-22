"use client";

import { useId, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/cn";
import { useDebouncedValue } from "@/lib/useDebouncedValue";
import { ApiError, isMissingKeyError } from "@/api/client";
import type { InstrumentSearchResultView } from "@/api/types";
import { useSymbolSearch } from "../hooks";

/** The minimal shape a picker hands back. Real search results are a superset of
 *  this, so they satisfy it directly; a raw typed ticker is synthesized to it. */
export type SymbolPick = Pick<
  InstrumentSearchResultView,
  "symbol" | "instrument_name" | "asset_type"
>;

/** Type-ahead search over symbol AND company name.
 *
 *  Two modes:
 *  - Default (navigate): selecting a result routes to `{basePath}/{symbol}`
 *    (Markets by default; the Intelligence page points it at itself).
 *  - Picker (`onSelect` given): selecting a result calls `onSelect(pick)` and
 *    fills the box with the chosen symbol instead of navigating — used by the
 *    trade desk and the SIP form. In this mode, pressing Enter with no matching
 *    result accepts the raw typed ticker, so a known symbol still works even if
 *    search returns nothing. */
export function SymbolSearch({
  autoFocus,
  placeholder = "Search symbol or company…",
  basePath = "/markets",
  onSelect,
}: {
  autoFocus?: boolean;
  placeholder?: string;
  basePath?: string;
  onSelect?: (pick: SymbolPick) => void;
}) {
  const router = useRouter();
  const [term, setTerm] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const listId = useId();
  const blurTimer = useRef<number | null>(null);

  const debounced = useDebouncedValue(term, 300);
  const q = useSymbolSearch(debounced);
  const results = q.data?.results ?? [];
  const showPanel = open && term.trim().length >= 1;

  function pick(result: SymbolPick) {
    if (onSelect) {
      onSelect({ ...result, symbol: result.symbol.toUpperCase() });
      setTerm(result.symbol.toUpperCase());
      setOpen(false);
      return;
    }
    setOpen(false);
    setTerm("");
    router.push(`${basePath}/${encodeURIComponent(result.symbol)}`);
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (!showPanel) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      const chosen = results[active];
      if (chosen) {
        e.preventDefault();
        pick(chosen);
      } else if (onSelect && !q.isLoading && term.trim()) {
        // No match, but the user typed something they mean literally (e.g. an
        // exact ticker search doesn't know). Accept it as a raw symbol.
        e.preventDefault();
        pick({ symbol: term.trim(), instrument_name: term.trim(), asset_type: "stock" });
      }
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div className="relative">
      <input
        role="combobox"
        aria-expanded={showPanel}
        aria-controls={listId}
        aria-autocomplete="list"
        autoFocus={autoFocus}
        value={term}
        placeholder={placeholder}
        onChange={(e) => {
          setTerm(e.target.value);
          setActive(0);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => {
          blurTimer.current = window.setTimeout(() => setOpen(false), 120);
        }}
        onKeyDown={onKeyDown}
        className="h-10 w-full rounded border border-line-2 bg-panel-2 px-3 text-sm text-fg placeholder:text-fg-mute focus:border-fg-mute focus:outline-none"
      />

      {showPanel && (
        <div
          id={listId}
          role="listbox"
          className="absolute z-20 mt-1 max-h-80 w-full overflow-y-auto rounded border border-line-2 bg-panel shadow-[0_8px_24px_rgba(0,0,0,0.5)]"
          onMouseDown={(e) => {
            // keep focus so onBlur doesn't close before the click registers
            e.preventDefault();
            if (blurTimer.current) window.clearTimeout(blurTimer.current);
          }}
        >
          {q.isLoading ? (
            <Note>Searching…</Note>
          ) : q.isError ? (
            <Note tone="down">
              {isMissingKeyError(q.error)
                ? "Search needs a market-data key on the backend."
                : (q.error as ApiError).message}
            </Note>
          ) : results.length === 0 ? (
            <Note>No matches for “{debounced.trim()}”.</Note>
          ) : (
            <ul>
              {results.map((r, i) => (
                <li key={`${r.symbol}-${i}`} role="option" aria-selected={i === active}>
                  <button
                    type="button"
                    onClick={() => pick(r)}
                    onMouseEnter={() => setActive(i)}
                    className={cn(
                      "flex w-full items-center gap-3 px-3 py-2 text-left",
                      i === active ? "bg-panel-2" : "hover:bg-panel-2/60",
                    )}
                  >
                    <span className="w-24 shrink-0 truncate font-mono text-xs text-fg">{r.symbol}</span>
                    <span className="min-w-0 flex-1 truncate text-xs text-fg-dim">
                      {r.instrument_name}
                    </span>
                    {r.asset_type === "mutual_fund" ? (
                      <span className="shrink-0 rounded-sm bg-panel-2 px-1.5 py-0.5 font-mono text-[0.625rem] uppercase tracking-wider text-fg-mute">
                        Fund
                      </span>
                    ) : (
                      r.sector && (
                        <span className="hidden shrink-0 font-mono text-[0.625rem] uppercase tracking-wider text-fg-mute sm:inline">
                          {r.sector}
                        </span>
                      )
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

function Note({ children, tone }: { children: React.ReactNode; tone?: "down" }) {
  return (
    <p className={cn("px-3 py-3 text-2xs", tone === "down" ? "text-down" : "text-fg-mute")}>
      {children}
    </p>
  );
}
