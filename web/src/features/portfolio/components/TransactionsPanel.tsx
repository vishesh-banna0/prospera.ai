"use client";

import { Panel } from "@/components/ui/Panel";
import { DataTable, type Column } from "@/components/ui/Table";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { IconWindow } from "@/components/ui/icons";
import { formatINR, formatQty } from "@/lib/money";
import { ApiError } from "@/api/client";
import type { TransactionView } from "@/api/types";
import { useTransactions } from "../hooks";

const typeTone: Record<string, BadgeTone> = {
  buy: "up",
  sell: "down",
  deposit: "neutral",
  withdrawal: "warn",
};

const timeFmt = new Intl.DateTimeFormat("en-IN", {
  day: "2-digit",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

function fmtTime(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : timeFmt.format(d);
}

const columns: Column<TransactionView>[] = [
  { header: "When", cell: (t) => <span className="text-fg-dim">{fmtTime(t.executed_at)}</span> },
  {
    header: "Type",
    cell: (t) => (
      <Badge tone={typeTone[t.transaction_type] ?? "neutral"} withTick={false}>
        {t.transaction_type}
      </Badge>
    ),
  },
  { header: "Symbol", cell: (t) => t.symbol ?? <span className="text-fg-mute">—</span> },
  {
    header: "Qty",
    align: "right",
    cell: (t) => (t.quantity == null ? <span className="text-fg-mute">—</span> : formatQty(t.quantity)),
  },
  { header: "Amount", align: "right", cell: (t) => formatINR(t.amount) },
];

export function TransactionsPanel({ id }: { id: string }) {
  const q = useTransactions(id);

  return (
    <Panel label="Transactions" bodyClassName={q.data && q.data.length ? "p-0" : "p-3"}>
      {q.isLoading ? (
        <TableSkeleton rows={4} />
      ) : q.isError ? (
        <ErrorState detail={(q.error as ApiError).message} onRetry={() => q.refetch()} />
      ) : (
        <DataTable
          columns={columns}
          rows={q.data ?? []}
          getRowKey={(t) => t.transaction_id}
          minWidth="34rem"
          empty={
            <EmptyState icon={<IconWindow />} title="No transactions yet">
              Deposits, withdrawals, and trades are recorded here as an append-only
              ledger.
            </EmptyState>
          }
        />
      )}
    </Panel>
  );
}
