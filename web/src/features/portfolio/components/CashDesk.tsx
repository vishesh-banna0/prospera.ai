"use client";

import { useState } from "react";
import { Panel } from "@/components/ui/Panel";
import { Button } from "@/components/ui/Button";
import { Input, Field } from "@/components/ui/Input";
import { cn } from "@/lib/cn";
import { formatINR } from "@/lib/money";
import { ApiError } from "@/api/client";
import { useCashMutation } from "../hooks";

type Kind = "deposit" | "withdraw";

/** Add or remove virtual cash. The action name carries through to the result:
 *  "Deposit" produces "Deposited ₹…". */
export function CashDesk({ id }: { id: string }) {
  const [kind, setKind] = useState<Kind>("deposit");
  const [amount, setAmount] = useState("");
  const [done, setDone] = useState<string | null>(null);
  const mutation = useCashMutation(id);

  const value = Number(amount);
  const valid = amount.trim() !== "" && Number.isFinite(value) && value > 0;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!valid) return;
    setDone(null);
    mutation.mutate(
      { kind, amount: value },
      {
        onSuccess: (ack) => {
          setDone(
            `${kind === "deposit" ? "Deposited" : "Withdrew"} ${formatINR(ack.amount)}`,
          );
          setAmount("");
        },
      },
    );
  }

  return (
    <Panel label="Cash desk">
      <div className="mb-3 grid grid-cols-2 gap-1 rounded border border-line-2 p-0.5">
        <Toggle active={kind === "deposit"} onClick={() => setKind("deposit")}>
          Deposit
        </Toggle>
        <Toggle active={kind === "withdraw"} onClick={() => setKind("withdraw")}>
          Withdraw
        </Toggle>
      </div>

      <form onSubmit={submit} className="flex flex-col gap-3">
        <Field label="Amount (₹)" htmlFor="cash-amount">
          <Input
            id="cash-amount"
            inputMode="decimal"
            placeholder="1,00,000"
            value={amount}
            onChange={(e) => {
              setAmount(e.target.value.replace(/[^0-9.]/g, ""));
              setDone(null);
            }}
            invalid={mutation.isError}
            mono
          />
        </Field>
        <Button type="submit" variant="primary" size="sm" loading={mutation.isPending} disabled={!valid}>
          {kind === "deposit" ? "Deposit cash" : "Withdraw cash"}
        </Button>
      </form>

      {mutation.isError && (
        <p className="mt-2 break-words font-mono text-2xs text-down">
          {(mutation.error as ApiError).message}
        </p>
      )}
      {done && !mutation.isError && (
        <p className="mt-2 font-mono text-2xs text-up">{done}</p>
      )}
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
