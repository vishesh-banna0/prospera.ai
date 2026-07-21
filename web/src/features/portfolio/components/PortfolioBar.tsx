"use client";

import { useState } from "react";
import { cn } from "@/lib/cn";
import { CreatePortfolioForm } from "./CreatePortfolioForm";
import type { PortfolioRef } from "../registry";

/** Horizontal selector for the portfolios in the local registry, plus an inline
 *  "new" form. Works at every width by wrapping. */
export function PortfolioBar({
  list,
  selectedId,
  onSelect,
  onCreated,
}: {
  list: PortfolioRef[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onCreated: (ref: PortfolioRef) => void;
}) {
  const [adding, setAdding] = useState(false);

  return (
    <div className="flex flex-col gap-2 border-b border-line pb-3">
      <div className="flex flex-wrap items-center gap-1.5">
        {list.map((p) => {
          const active = p.id === selectedId;
          return (
            <button
              key={p.id}
              type="button"
              onClick={() => onSelect(p.id)}
              aria-current={active ? "true" : undefined}
              className={cn(
                "max-w-[12rem] truncate rounded border px-2.5 py-1 text-xs transition-colors",
                active
                  ? "border-line-2 bg-panel-2 font-medium text-fg"
                  : "border-line text-fg-dim hover:border-line-2 hover:text-fg",
              )}
            >
              {p.name}
            </button>
          );
        })}
        <button
          type="button"
          onClick={() => setAdding((v) => !v)}
          className="rounded border border-dashed border-line-2 px-2.5 py-1 font-mono text-2xs uppercase tracking-wider text-fg-mute hover:text-fg-dim"
        >
          {adding ? "close" : "+ new"}
        </button>
      </div>

      {adding && (
        <div className="pt-1">
          <CreatePortfolioForm
            autoFocus
            onCreated={(ref) => {
              onCreated(ref);
              setAdding(false);
            }}
          />
        </div>
      )}
    </div>
  );
}
