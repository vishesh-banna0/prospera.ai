"use client";

import { useEffect, useState } from "react";
import { Panel } from "@/components/ui/Panel";
import { Button } from "@/components/ui/Button";
import { Input, Field } from "@/components/ui/Input";
import { cn } from "@/lib/cn";
import { formatINR } from "@/lib/money";
import { ApiError } from "@/api/client";
import type { SipPlanView } from "@/api/types";
import { SymbolSearch, type SymbolPick } from "@/features/markets/components/SymbolSearch";
import { useSipPlans, useCreateSipPlan, useCancelSipPlan } from "../hooks";
import type { SipFrequency } from "../api";

/** Set up recurring, forward-looking investments (SIPs) — stocks or mutual funds.
 *  A plan invests a fixed amount on a schedule; each installment runs when its
 *  date arrives and you next open the portfolio (there's no live scheduler, so
 *  nothing happens between visits). Nothing is invested the moment you create a
 *  plan — the first installment waits for its first due date. */
export function SipPanel({ id }: { id: string }) {
  const plans = useSipPlans(id);
  const create = useCreateSipPlan(id);
  const cancel = useCancelSipPlan(id);

  const [symbol, setSymbol] = useState("");
  const [name, setName] = useState("");
  const [amount, setAmount] = useState("");
  const [frequency, setFrequency] = useState<SipFrequency>("monthly");
  const [start, setStart] = useState("");
  const [done, setDone] = useState<string | null>(null);

  // Default the start date on mount (not during render) to avoid a hydration
  // mismatch — same trick the backtest form uses.
  useEffect(() => {
    setStart(new Date().toISOString().slice(0, 10));
  }, []);

  const amt = Number(amount);
  const valid =
    symbol.trim() !== "" && Number.isFinite(amt) && amt > 0 && start !== "";

  function choose(pick: SymbolPick) {
    setSymbol(pick.symbol);
    setName(pick.instrument_name ?? "");
    setDone(null);
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!valid) return;
    setDone(null);
    create.mutate(
      { symbol, name: name || undefined, amount: amt, frequency, startDateISO: start },
      {
        onSuccess: (plan) => {
          setDone(`SIP set: ${formatINR(plan.amount)} ${labelFor(plan.frequency)} into ${plan.symbol}`);
          setSymbol("");
          setName("");
          setAmount("");
        },
      },
    );
  }

  const rows = plans.data ?? [];

  return (
    <Panel label="Recurring · SIP">
      <p className="mb-3 text-2xs text-fg-dim">
        Invest a fixed amount on a schedule into a stock or mutual fund. Installments
        run when their date arrives and you open this portfolio — the first one waits
        for its start date.
      </p>

      <form onSubmit={submit} className="flex flex-col gap-3">
        <div className="flex flex-col gap-1.5">
          <span className="eyebrow">Instrument</span>
          {symbol === "" ? (
            <SymbolSearch onSelect={choose} placeholder="Search stock or fund…" />
          ) : (
            <div className="flex items-center justify-between rounded border border-line-2 bg-panel-2 px-3 py-2">
              <div className="min-w-0">
                <span className="font-mono text-sm text-fg">{symbol}</span>
                {name && <span className="ml-2 truncate text-2xs text-fg-dim">{name}</span>}
              </div>
              <button
                type="button"
                onClick={() => {
                  setSymbol("");
                  setName("");
                  setDone(null);
                }}
                className="shrink-0 font-mono text-2xs uppercase tracking-wider text-fg-mute hover:text-fg"
              >
                Change
              </button>
            </div>
          )}
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Amount (₹)" htmlFor="sip-amount">
            <Input
              id="sip-amount"
              inputMode="decimal"
              placeholder="5,000"
              value={amount}
              onChange={(e) => {
                setAmount(e.target.value.replace(/[^0-9.]/g, ""));
                setDone(null);
              }}
              invalid={create.isError}
              mono
            />
          </Field>
          <Field label="Start date" htmlFor="sip-start">
            <Input
              id="sip-start"
              type="date"
              value={start}
              onChange={(e) => setStart(e.target.value)}
              mono
            />
          </Field>
        </div>

        <div className="flex flex-col gap-1.5">
          <span className="eyebrow">Frequency</span>
          <div className="grid grid-cols-2 gap-1 rounded border border-line-2 p-0.5 sm:max-w-xs">
            <FreqToggle active={frequency === "monthly"} onClick={() => setFrequency("monthly")}>
              Monthly
            </FreqToggle>
            <FreqToggle active={frequency === "weekly"} onClick={() => setFrequency("weekly")}>
              Weekly
            </FreqToggle>
          </div>
        </div>

        <Button type="submit" variant="primary" size="sm" loading={create.isPending} disabled={!valid}>
          Start SIP
        </Button>
      </form>

      {create.isError && (
        <p className="mt-2 break-words font-mono text-2xs text-down">
          {(create.error as ApiError).message}
        </p>
      )}
      {done && !create.isError && <p className="mt-2 font-mono text-2xs text-up">{done}</p>}

      {rows.length > 0 && (
        <ul className="mt-4 flex flex-col gap-2 border-t border-line pt-3">
          {rows.map((plan) => (
            <PlanRow
              key={plan.plan_id}
              plan={plan}
              onCancel={() => cancel.mutate(plan.plan_id)}
              cancelling={cancel.isPending && cancel.variables === plan.plan_id}
            />
          ))}
        </ul>
      )}
    </Panel>
  );
}

function PlanRow({
  plan,
  onCancel,
  cancelling,
}: {
  plan: SipPlanView;
  onCancel: () => void;
  cancelling: boolean;
}) {
  return (
    <li className="flex items-center justify-between gap-3 rounded border border-line-2 bg-panel-2 px-3 py-2">
      <div className="min-w-0">
        <div className="flex items-baseline gap-2">
          <span className="truncate text-xs text-fg">{plan.symbol_name || plan.symbol}</span>
          {plan.symbol_name && (
            <span className="shrink-0 font-mono text-[0.625rem] text-fg-mute">{plan.symbol}</span>
          )}
          {plan.status !== "active" && (
            <span className="shrink-0 rounded-sm bg-panel px-1.5 font-mono text-[0.625rem] uppercase tracking-wider text-fg-mute">
              {plan.status}
            </span>
          )}
        </div>
        <div className="mt-0.5 font-mono text-2xs text-fg-dim">
          <span className="text-fg">{formatINR(plan.amount)}</span> {labelFor(plan.frequency)} · next{" "}
          {fmtDate(plan.next_run_date)} · {plan.installments_run} done
          {plan.installments_skipped > 0 && (
            <span className="text-down"> · {plan.installments_skipped} skipped (low cash)</span>
          )}
        </div>
      </div>
      <button
        type="button"
        onClick={onCancel}
        disabled={cancelling}
        className="shrink-0 font-mono text-2xs uppercase tracking-wider text-fg-mute hover:text-down disabled:opacity-40"
      >
        {cancelling ? "…" : "Cancel"}
      </button>
    </li>
  );
}

function FreqToggle({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "rounded-sm px-2 py-1 font-mono text-2xs uppercase tracking-wider transition-colors",
        active ? "bg-panel text-fg" : "text-fg-mute hover:text-fg-dim",
      )}
    >
      {children}
    </button>
  );
}

function labelFor(frequency: string): string {
  return frequency === "weekly" ? "weekly" : "monthly";
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** Format a "YYYY-MM-DD" API date without constructing a Date (which would shift
 *  by timezone). */
function fmtDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  if (!y || !m || !d) return iso;
  return `${String(d).padStart(2, "0")} ${MONTHS[m - 1]} ${y}`;
}
