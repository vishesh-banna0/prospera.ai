"use client";

import { useId, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/cn";
import { useDebouncedValue } from "@/lib/useDebouncedValue";
import { ApiError, isMissingKeyError } from "@/api/client";
import { useSymbolSearch } from "../hooks";

/** Type-ahead symbol search. Selecting a result routes to `{basePath}/{symbol}`
 *  (Markets by default; the Intelligence page points it at itself). */
export function SymbolSearch({
  autoFocus,
  placeholder = "Search symbol or company…",
  basePath = "/markets",
}: {
  autoFocus?: boolean;
  placeholder?: string;
  basePath?: string;
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

  function choose(symbol: string) {
    setOpen(false);
    setTerm("");
    router.push(`${basePath}/${encodeURIComponent(symbol)}`);
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
      const pick = results[active];
      if (pick) {
        e.preventDefault();
        choose(pick.symbol);
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
                    onClick={() => choose(r.symbol)}
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
                    {r.sector && (
                      <span className="hidden shrink-0 font-mono text-[0.625rem] uppercase tracking-wider text-fg-mute sm:inline">
                        {r.sector}
                      </span>
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
