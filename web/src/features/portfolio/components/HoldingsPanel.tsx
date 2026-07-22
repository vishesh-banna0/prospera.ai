"use client";

import { Panel } from "@/components/ui/Panel";
import { DataTable, type Column } from "@/components/ui/Table";
import { SignedNumber } from "@/components/ui/SignedNumber";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { IconWindow } from "@/components/ui/icons";
import { formatINR, formatQty } from "@/lib/money";
import { ApiError } from "@/api/client";
import type { HoldingView } from "@/api/types";
import { useHoldings } from "../hooks";

const columns: Column<HoldingView>[] = [
  {
    header: "Symbol",
    cell: (h) => (
      <span className="flex items-center gap-2">
        <span className="text-fg">{h.symbol}</span>
        {h.symbol.toUpperCase().endsWith(".MF") && (
          <span className="rounded-sm bg-panel-2 px-1.5 font-mono text-[0.625rem] uppercase tracking-wider text-fg-mute">
            Fund
          </span>
        )}
      </span>
    ),
  },
  { header: "Qty", align: "right", cell: (h) => formatQty(h.quantity) },
  { header: "Avg cost", align: "right", cell: (h) => formatINR(h.average_cost) },
  { header: "Market value", align: "right", cell: (h) => formatINR(h.market_value ?? null) },
  {
    header: "Unrealized",
    align: "right",
    cell: (h) => <SignedNumber value={h.unrealized_pnl ?? null} kind="inr" decimals={2} />,
  },
  {
    header: "Return",
    align: "right",
    cell: (h) => <SignedNumber value={h.return_percentage ?? null} kind="pct" />,
  },
];

export function HoldingsPanel({ id }: { id: string }) {
  const q = useHoldings(id);

  return (
    <Panel label="Holdings" bodyClassName={q.data && q.data.length ? "p-0" : "p-3"}>
      {q.isLoading ? (
        <TableSkeleton rows={3} />
      ) : q.isError ? (
        <ErrorState detail={(q.error as ApiError).message} onRetry={() => q.refetch()} />
      ) : (
        <DataTable
          columns={columns}
          rows={q.data ?? []}
          getRowKey={(h) => h.symbol}
          minWidth="34rem"
          empty={
            <EmptyState icon={<IconWindow />} title="No holdings yet">
              Buy a stock from the trade desk and it will appear here, priced live
              in rupees.
            </EmptyState>
          }
        />
      )}
    </Panel>
  );
}
