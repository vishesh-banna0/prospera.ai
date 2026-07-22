"use client";

import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/States";
import { IconGaugeEmpty } from "@/components/ui/icons";
import { usePerformance } from "@/features/portfolio/hooks";
import { usePortfolioRegistry, type PortfolioRef } from "@/features/portfolio/registry";
import { PortfolioBar } from "@/features/portfolio/components/PortfolioBar";
import { PortfolioHeader } from "@/features/portfolio/components/PortfolioHeader";
import { PerformancePanel } from "@/features/portfolio/components/PerformancePanel";
import { HoldingsPanel } from "@/features/portfolio/components/HoldingsPanel";
import { TransactionsPanel } from "@/features/portfolio/components/TransactionsPanel";
import { CashDesk } from "@/features/portfolio/components/CashDesk";
import { TradeDesk } from "@/features/portfolio/components/TradeDesk";
import { SipPanel } from "@/features/portfolio/components/SipPanel";
import { CreatePortfolioForm } from "@/features/portfolio/components/CreatePortfolioForm";

export default function PortfolioPage() {
  const registry = usePortfolioRegistry();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Keep the selection valid as the list changes (create / delete / first load).
  useEffect(() => {
    if (registry.list === null) return;
    if (registry.list.length === 0) {
      setSelectedId(null);
      return;
    }
    const stillThere = registry.list.some((p) => p.id === selectedId);
    if (!stillThere) setSelectedId(registry.list[0]?.id ?? null);
  }, [registry.list, selectedId]);

  function handleCreated(ref: PortfolioRef) {
    registry.add(ref);
    setSelectedId(ref.id);
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-5 sm:px-6">
      <header className="mb-4">
        <p className="eyebrow">Desk · Portfolio Center</p>
        <h1 className="mt-1 font-display text-xl font-bold text-fg">Paper trading</h1>
        <p className="mt-1 max-w-2xl text-2xs text-fg-dim">
          Virtual cash, real prices, real profit and loss — all in rupees. Nothing
          here is a real order.
        </p>
      </header>

      {registry.list === null ? (
        <LoadingShell />
      ) : registry.list.length === 0 ? (
        <EmptyState
          icon={<IconGaugeEmpty />}
          title="No portfolios yet"
          className="mt-8"
          action={<CreatePortfolioForm autoFocus onCreated={handleCreated} />}
        >
          Create your first paper-trading portfolio to start. You get virtual cash
          to buy and sell real stocks at live prices.
        </EmptyState>
      ) : (
        <div className="flex flex-col gap-4">
          <PortfolioBar
            list={registry.list}
            selectedId={selectedId}
            onSelect={setSelectedId}
            onCreated={handleCreated}
          />

          {selectedId && (
            <Dashboard
              key={selectedId}
              id={selectedId}
              fallbackName={registry.list.find((p) => p.id === selectedId)?.name ?? "Portfolio"}
              onRenamed={(name) => registry.rename(selectedId, name)}
              onDeleted={() => {
                registry.remove(selectedId);
                setSelectedId(null);
              }}
            />
          )}
        </div>
      )}
    </div>
  );
}

function Dashboard({
  id,
  fallbackName,
  onRenamed,
  onDeleted,
}: {
  id: string;
  fallbackName: string;
  onRenamed: (name: string) => void;
  onDeleted: () => void;
}) {
  const qc = useQueryClient();
  const performance = usePerformance(id);

  // Reading performance runs any due SIP installments on the backend (lazy
  // catch-up). Once it settles, refresh the panels those installments could have
  // changed so holdings, transactions, and the plan list stay in step — the same
  // idea as refreshing after a trade, but the trade here is a server-side effect.
  const settledAt = performance.dataUpdatedAt;
  useEffect(() => {
    if (!settledAt) return;
    qc.invalidateQueries({ queryKey: ["holdings", id] });
    qc.invalidateQueries({ queryKey: ["transactions", id] });
    qc.invalidateQueries({ queryKey: ["sip-plans", id] });
  }, [settledAt, id, qc]);

  return (
    <div className="flex flex-col gap-4">
      <PortfolioHeader id={id} fallbackName={fallbackName} onRenamed={onRenamed} onDeleted={onDeleted} />
      <PerformancePanel id={id} />
      <div className="grid gap-4 lg:grid-cols-2">
        <CashDesk id={id} />
        <TradeDesk id={id} />
      </div>
      <SipPanel id={id} />
      <HoldingsPanel id={id} />
      <TransactionsPanel id={id} />
    </div>
  );
}

function LoadingShell() {
  return (
    <div className="flex flex-col gap-4">
      <Skeleton className="h-8 w-64" />
      <Skeleton className="h-24 w-full" />
      <div className="grid gap-4 lg:grid-cols-2">
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    </div>
  );
}
