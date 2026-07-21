"use client";

import { Panel } from "@/components/ui/Panel";
import { SignedNumber } from "@/components/ui/SignedNumber";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { IconKey } from "@/components/ui/icons";
import { formatINR, formatCompactNumber, toNumber } from "@/lib/money";
import { ApiError, isMissingKeyError } from "@/api/client";
import { useQuote } from "../hooks";

const asOfFmt = new Intl.DateTimeFormat("en-IN", {
  day: "2-digit",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

export function QuotePanel({ symbol }: { symbol: string }) {
  const q = useQuote(symbol);

  return (
    <Panel
      label="Quote"
      aside={
        q.data ? (
          <span className="font-mono text-[0.625rem] uppercase tracking-wider text-fg-mute">
            {q.isFetching
              ? "syncing"
              : q.data.as_of
                ? `as of ${asOfFmt.format(new Date(q.data.as_of))}`
                : "live"}
          </span>
        ) : null
      }
    >
      {q.isLoading ? (
        <div className="flex flex-col gap-3">
          <Skeleton className="h-9 w-40" />
          <Skeleton className="h-4 w-28" />
          <div className="grid grid-cols-2 gap-2 pt-2 sm:grid-cols-3">
            {Array.from({ length: 5 }, (_, i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        </div>
      ) : q.isError ? (
        isMissingKeyError(q.error) ? (
          <EmptyState icon={<IconKey />} title="Live quotes need a key" tone="warn">
            Add a Finnhub key to the backend for live quotes. History and company
            details may still load.
          </EmptyState>
        ) : (
          <ErrorState detail={(q.error as ApiError).message} onRetry={() => q.refetch()} />
        )
      ) : q.data ? (
        <QuoteBody
          last={q.data.last_price}
          prev={q.data.previous_close}
          open={q.data.open_price}
          high={q.data.high_price}
          low={q.data.low_price}
          volume={q.data.volume}
        />
      ) : null}
    </Panel>
  );
}

function QuoteBody({
  last,
  prev,
  open,
  high,
  low,
  volume,
}: {
  last: string;
  prev: string | null | undefined;
  open: string | null | undefined;
  high: string | null | undefined;
  low: string | null | undefined;
  volume: number | null | undefined;
}) {
  const lastN = toNumber(last);
  const prevN = toNumber(prev);
  const change = lastN !== null && prevN !== null ? lastN - prevN : null;
  const pct = change !== null && prevN ? (change / prevN) * 100 : null;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <span className="font-mono text-2xl leading-none text-fg tnum">{formatINR(last)}</span>
        {change !== null && (
          <span className="flex items-baseline gap-2 text-sm">
            <SignedNumber value={change} kind="inr" decimals={2} />
            {pct !== null && <SignedNumber value={pct} kind="pct" withGlyph={false} />}
          </span>
        )}
        <span className="font-mono text-[0.625rem] uppercase tracking-wider text-fg-mute">
          vs prev close
        </span>
      </div>

      <dl className="grid grid-cols-2 gap-x-6 gap-y-2 border-t border-line pt-3 sm:grid-cols-3">
        <Field label="Open" value={formatINR(open)} />
        <Field label="High" value={formatINR(high)} />
        <Field label="Low" value={formatINR(low)} />
        <Field label="Prev close" value={formatINR(prev)} />
        <Field label="Volume" value={volume == null ? "—" : formatCompactNumber(volume)} />
      </dl>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="eyebrow">{label}</dt>
      <dd className="font-mono text-xs text-fg tnum">{value}</dd>
    </div>
  );
}
