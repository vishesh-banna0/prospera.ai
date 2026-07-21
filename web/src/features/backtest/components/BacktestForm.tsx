"use client";

import { useEffect, useState } from "react";
import { Panel } from "@/components/ui/Panel";
import { Button } from "@/components/ui/Button";
import { Input, Field } from "@/components/ui/Input";
import { cn } from "@/lib/cn";
import type { BacktestInput, Strategy } from "../api";

/** Collects the simulation inputs. Dates default on mount (not in the initial
 *  render) so server and client agree — no hydration mismatch. */
export function BacktestForm({
  onRun,
  pending,
}: {
  onRun: (input: BacktestInput) => void;
  pending: boolean;
}) {
  const [strategy, setStrategy] = useState<Strategy>("lumpsum");
  const [symbol, setSymbol] = useState("AAPL");
  const [amount, setAmount] = useState("100000");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");

  useEffect(() => {
    const now = new Date();
    setEnd(now.toISOString().slice(0, 10));
    const s = new Date(now.getFullYear() - 2, now.getMonth(), now.getDate());
    setStart(s.toISOString().slice(0, 10));
  }, []);

  const amt = Number(amount);
  const valid =
    symbol.trim() !== "" &&
    Number.isFinite(amt) &&
    amt > 0 &&
    start !== "" &&
    end !== "" &&
    start < end;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!valid) return;
    onRun({
      strategy,
      symbol,
      amount: amt,
      startISO: `${start}T00:00:00Z`,
      endISO: `${end}T00:00:00Z`,
    });
  }

  return (
    <Panel label="Simulation">
      <form onSubmit={submit} className="flex flex-col gap-4">
        <div className="grid grid-cols-2 gap-1 rounded border border-line-2 p-0.5 sm:max-w-xs">
          <Toggle active={strategy === "lumpsum"} onClick={() => setStrategy("lumpsum")}>
            Lump sum
          </Toggle>
          <Toggle active={strategy === "sip"} onClick={() => setStrategy("sip")}>
            Monthly SIP
          </Toggle>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Field label="Symbol" htmlFor="bt-symbol" hint="e.g. AAPL, MSFT">
            <Input
              id="bt-symbol"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              className="font-mono uppercase"
            />
          </Field>
          <Field
            label={strategy === "lumpsum" ? "Amount (₹)" : "Monthly amount (₹)"}
            htmlFor="bt-amount"
          >
            <Input
              id="bt-amount"
              inputMode="decimal"
              value={amount}
              onChange={(e) => setAmount(e.target.value.replace(/[^0-9.]/g, ""))}
              mono
            />
          </Field>
          <Field label="Start" htmlFor="bt-start">
            <Input id="bt-start" type="date" value={start} max={end || undefined} onChange={(e) => setStart(e.target.value)} mono />
          </Field>
          <Field label="End" htmlFor="bt-end">
            <Input id="bt-end" type="date" value={end} min={start || undefined} onChange={(e) => setEnd(e.target.value)} mono />
          </Field>
        </div>

        <div className="flex items-center gap-3">
          <Button type="submit" variant="primary" loading={pending} disabled={!valid}>
            Run simulation
          </Button>
          {start !== "" && end !== "" && start >= end && (
            <span className="font-mono text-2xs text-down">Start must be before end.</span>
          )}
        </div>
      </form>
    </Panel>
  );
}

function Toggle({
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
        active ? "bg-panel-2 text-fg" : "text-fg-mute hover:text-fg-dim",
      )}
    >
      {children}
    </button>
  );
}
