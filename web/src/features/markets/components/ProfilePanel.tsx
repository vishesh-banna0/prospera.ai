"use client";

import { useState } from "react";
import { Panel } from "@/components/ui/Panel";
import { Skeleton } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/States";
import { formatCompactINR, formatCompactNumber } from "@/lib/money";
import { ApiError } from "@/api/client";
import type { CompanyProfileView } from "@/api/types";
import { useProfile } from "../hooks";

export function ProfilePanel({ symbol }: { symbol: string }) {
  const q = useProfile(symbol);

  return (
    <Panel label="Company">
      {q.isLoading ? (
        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {Array.from({ length: 4 }, (_, i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
          <Skeleton className="h-16 w-full" />
        </div>
      ) : q.isError ? (
        <ErrorState detail={(q.error as ApiError).message} onRetry={() => q.refetch()} />
      ) : q.data ? (
        <Body p={q.data} />
      ) : null}
    </Panel>
  );
}

function Body({ p }: { p: CompanyProfileView }) {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="font-display text-base font-semibold text-fg">{p.instrument_name}</h2>
        <p className="font-mono text-2xs text-fg-mute">
          {p.symbol} · {p.exchange}
        </p>
      </div>

      <dl className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-4">
        <Fact label="Sector" value={p.sector ?? "—"} />
        <Fact label="Industry" value={p.industry ?? "—"} />
        <Fact label="Market cap" value={p.market_cap ? formatCompactINR(p.market_cap) : "—"} mono />
        <Fact
          label="Employees"
          value={p.employees != null ? formatCompactNumber(p.employees) : "—"}
          mono
        />
        <Fact label="Country" value={p.country ?? "—"} />
      </dl>

      {p.description && <Description text={p.description} />}

      {p.website && (
        <a
          href={p.website}
          target="_blank"
          rel="noopener noreferrer"
          className="w-fit font-mono text-2xs text-fg-dim underline decoration-line-2 underline-offset-2 hover:text-fg"
        >
          {p.website.replace(/^https?:\/\//, "")} ↗
        </a>
      )}
    </div>
  );
}

function Fact({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex min-w-0 flex-col gap-0.5">
      <dt className="eyebrow">{label}</dt>
      <dd className={mono ? "font-mono text-xs text-fg tnum" : "truncate text-xs text-fg"}>{value}</dd>
    </div>
  );
}

function Description({ text }: { text: string }) {
  const [open, setOpen] = useState(false);
  const long = text.length > 320;
  return (
    <div className="border-t border-line pt-3">
      <p className={open ? "text-2xs leading-relaxed text-fg-dim" : "line-clamp-3 text-2xs leading-relaxed text-fg-dim"}>
        {text}
      </p>
      {long && (
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="mt-1 font-mono text-[0.625rem] uppercase tracking-wider text-fg-mute hover:text-fg-dim"
        >
          {open ? "show less" : "show more"}
        </button>
      )}
    </div>
  );
}
