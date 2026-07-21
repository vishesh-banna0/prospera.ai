"use client";

import { useState } from "react";
import { Panel } from "@/components/ui/Panel";
import { Button } from "@/components/ui/Button";
import { Input, Field } from "@/components/ui/Input";
import { cn } from "@/lib/cn";
import { formatQty } from "@/lib/money";
import { ApiError } from "@/api/client";
import { useTradeMutation } from "../hooks";
import type { OrderSide } from "../api";

/** Buy or sell a real stock at a real (INR-converted) price. Buy/Sell are the one
 *  place a control speaks in the market's direction colors. */
export function TradeDesk({ id }: { id: string }) {
  const [side, setSide] = useState<OrderSide>("buy");
  const [symbol, setSymbol] = useState("");
  const [qty, setQty] = useState("");
  const [done, setDone] = useState<string | null>(null);
  const mutation = useTradeMutation(id);

  const quantity = Number(qty);
  const valid =
    symbol.trim() !== "" && qty.trim() !== "" && Number.isFinite(quantity) && quantity > 0;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!valid) return;
    setDone(null);
    mutation.mutate(
      { side, symbol, quantity },
      {
        onSuccess: (ack) => {
          setDone(
            `${side === "buy" ? "Bought" : "Sold"} ${formatQty(ack.quantity)} ${ack.symbol}`,
          );
          setQty("");
        },
      },
    );
  }

  return (
    <Panel label="Trade desk">
      <div className="mb-3 grid grid-cols-2 gap-1 rounded border border-line-2 p-0.5">
        <SideToggle side="buy" active={side === "buy"} onClick={() => setSide("buy")} />
        <SideToggle side="sell" active={side === "sell"} onClick={() => setSide("sell")} />
      </div>

      <form onSubmit={submit} className="flex flex-col gap-3">
        <Field label="Symbol" htmlFor="trade-symbol" hint="e.g. AAPL, RELIANCE.NS">
          <Input
            id="trade-symbol"
            placeholder="AAPL"
            value={symbol}
            onChange={(e) => {
              setSymbol(e.target.value.toUpperCase());
              setDone(null);
            }}
            invalid={mutation.isError}
            className="font-mono uppercase"
          />
        </Field>
        <Field label="Quantity" htmlFor="trade-qty">
          <Input
            id="trade-qty"
            inputMode="decimal"
            placeholder="10"
            value={qty}
            onChange={(e) => {
              setQty(e.target.value.replace(/[^0-9.]/g, ""));
              setDone(null);
            }}
            invalid={mutation.isError}
            mono
          />
        </Field>
        <Button
          type="submit"
          variant={side === "buy" ? "buy" : "sell"}
          size="sm"
          loading={mutation.isPending}
          disabled={!valid}
        >
          {side === "buy" ? "Buy" : "Sell"}
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

function SideToggle({
  side,
  active,
  onClick,
}: {
  side: OrderSide;
  active: boolean;
  onClick: () => void;
}) {
  const activeClass = side === "buy" ? "bg-up/15 text-up" : "bg-down/15 text-down";
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "rounded-sm px-2 py-1 font-mono text-2xs uppercase tracking-wider transition-colors",
        active ? activeClass : "text-fg-mute hover:text-fg-dim",
      )}
    >
      {side}
    </button>
  );
}
