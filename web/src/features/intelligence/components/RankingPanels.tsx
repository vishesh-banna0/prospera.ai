"use client";

import Link from "next/link";
import { Panel } from "@/components/ui/Panel";
import { DataTable, type Column } from "@/components/ui/Table";
import { Badge, toneForVerdict } from "@/components/ui/Badge";
import { SignedNumber } from "@/components/ui/SignedNumber";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { IconGaugeEmpty } from "@/components/ui/icons";
import { formatPct } from "@/lib/money";
import { ApiError } from "@/api/client";
import type {
  CompanyScoreView,
  FusedSignalView,
  PredictionView,
  ReasonedOpinionView,
} from "@/api/types";
import { useCompanyScores, usePredictions, useSignals, useOpinions } from "../hooks";

function SymLink({ symbol }: { symbol: string }) {
  return (
    <Link
      href={`/intelligence/${encodeURIComponent(symbol)}`}
      className="font-mono text-fg underline decoration-line-2 underline-offset-2 hover:decoration-fg-mute"
    >
      {symbol}
    </Link>
  );
}

/** Shared frame: loading skeleton, error, or a table with its own empty state. */
function RankingFrame({
  label,
  isLoading,
  error,
  onRetry,
  isEmpty,
  emptyLabel,
  children,
}: {
  label: string;
  isLoading: boolean;
  error: unknown;
  onRetry: () => void;
  isEmpty: boolean;
  emptyLabel: string;
  children: React.ReactNode;
}) {
  return (
    <Panel label={label} bodyClassName={isEmpty || isLoading || error ? "p-3" : "p-0"}>
      {isLoading ? (
        <TableSkeleton rows={3} />
      ) : error ? (
        <ErrorState detail={(error as ApiError).message} onRetry={onRetry} />
      ) : isEmpty ? (
        <EmptyState icon={<IconGaugeEmpty />} title={emptyLabel}>
          Analyze a symbol above and its result lands here.
        </EmptyState>
      ) : (
        children
      )}
    </Panel>
  );
}

export function CompanyScoresPanel() {
  const q = useCompanyScores();
  const rows = q.data?.companies ?? [];
  const columns: Column<CompanyScoreView>[] = [
    { header: "Symbol", cell: (r) => <SymLink symbol={r.symbol} /> },
    { header: "Score", align: "right", cell: (r) => r.overall_score.toFixed(0) },
    { header: "Rating", align: "right", cell: (r) => <Badge tone={toneForVerdict(r.rating)} withTick={false}>{r.rating}</Badge> },
  ];
  return (
    <RankingFrame label="Company scores" isLoading={q.isLoading} error={q.error} onRetry={() => q.refetch()} isEmpty={rows.length === 0} emptyLabel="No scores yet">
      <DataTable columns={columns} rows={rows} getRowKey={(r) => r.symbol} minWidth="20rem" />
    </RankingFrame>
  );
}

export function SignalsPanel() {
  const q = useSignals();
  const rows = q.data?.signals ?? [];
  const columns: Column<FusedSignalView>[] = [
    { header: "Symbol", cell: (r) => <SymLink symbol={r.symbol} /> },
    { header: "Action", cell: (r) => <Badge tone={toneForVerdict(r.action)}>{r.action}</Badge> },
    { header: "Score", align: "right", cell: (r) => <SignedNumber value={r.score} kind="pct" withGlyph={false} decimals={2} /> },
    { header: "Conf.", align: "right", cell: (r) => formatPct(r.confidence * 100, 0) },
  ];
  return (
    <RankingFrame label="Fused signals" isLoading={q.isLoading} error={q.error} onRetry={() => q.refetch()} isEmpty={rows.length === 0} emptyLabel="No signals yet">
      <DataTable columns={columns} rows={rows} getRowKey={(r) => r.symbol} minWidth="24rem" />
    </RankingFrame>
  );
}

export function PredictionsPanel() {
  const q = usePredictions();
  const rows = q.data?.predictions ?? [];
  const columns: Column<PredictionView>[] = [
    { header: "Symbol", cell: (r) => <SymLink symbol={r.symbol} /> },
    { header: "Dir.", cell: (r) => <Badge tone={toneForVerdict(r.direction)}>{r.direction}</Badge> },
    { header: "P(up)", align: "right", cell: (r) => r.probability_up.toFixed(2) },
    { header: "Exp.", align: "right", cell: (r) => <SignedNumber value={r.expected_return_pct} kind="pct" /> },
  ];
  return (
    <RankingFrame label="Predictions" isLoading={q.isLoading} error={q.error} onRetry={() => q.refetch()} isEmpty={rows.length === 0} emptyLabel="No predictions yet">
      <DataTable columns={columns} rows={rows} getRowKey={(r) => r.prediction_id} minWidth="24rem" />
    </RankingFrame>
  );
}

export function OpinionsPanel() {
  const q = useOpinions();
  const rows = q.data?.opinions ?? [];
  const columns: Column<ReasonedOpinionView>[] = [
    { header: "Symbol", cell: (r) => <SymLink symbol={r.symbol} /> },
    { header: "Stance", cell: (r) => <Badge tone={toneForVerdict(r.stance)}>{r.stance}</Badge> },
    { header: "Conf.", align: "right", cell: (r) => formatPct(r.confidence * 100, 0) },
  ];
  return (
    <RankingFrame label="Opinions" isLoading={q.isLoading} error={q.error} onRetry={() => q.refetch()} isEmpty={rows.length === 0} emptyLabel="No opinions yet">
      <DataTable columns={columns} rows={rows} getRowKey={(r) => r.symbol} minWidth="20rem" />
    </RankingFrame>
  );
}
