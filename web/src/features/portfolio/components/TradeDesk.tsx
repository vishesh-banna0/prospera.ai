"use client";

import { useState } from "react";
import { Panel } from "@/components/ui/Panel";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { cn } from "@/lib/cn";
import { formatINR, formatQty, toNumber } from "@/lib/money";
import { ApiError } from "@/api/client";
import { SymbolSearch, type SymbolPick } from "@/features/markets/components/SymbolSearch";
import { useQuote } from "@/features/markets/hooks";
import { useTradeMutation, usePerformance, useHoldings } from "../hooks";
import type { OrderSide } from "../api";

/** Buy or sell a real stock at a real (INR-converted) price. Unlike before, the
 *  desk now shows the live price, what an order would cost (or return), and your
 *  available cash / held quantity — so you never have to guess the size.
 *  Buy/Sell are the one place a control speaks in the market's direction colors. */
export function TradeDesk({ id }: { id: string }) {
  const [side, setSide] = useState<OrderSide>("buy");
  const [symbol, setSymbol] = useState("");
  const [name, setName] = useState("");
  const [qty, setQty] = useState("");
  const [done, setDone] = useState<string | null>(null);
  const mutation = useTradeMutation(id);

  const quote = useQuote(symbol);
  const performance = usePerformance(id);
  const holdings = useHoldings(id);

  const price = toNumber(quote.data?.last_price);
  const cash = toNumber(performance.data?.cash_balance);
  const held = toNumber(holdings.data?.find((h) => h.symbol === symbol)?.quantity ?? null) ?? 0;

  const quantity = Number(qty);
  const hasQty = qty.trim() !== "" && Number.isFinite(quantity) && quantity > 0;
  const orderValue = price !== null && hasQty ? price * quantity : null;

  const maxAffordable =
    price !== null && price > 0 && cash !== null ? Math.floor(cash / price) : null;

  const overCash = side === "buy" && orderValue !== null && cash !== null && orderValue > cash;
  const overHeld = side === "sell" && hasQty && quantity > held;
  const valid = symbol.trim() !== "" && hasQty && !overCash && !overHeld;

  function choose(pick: SymbolPick) {
    setSymbol(pick.symbol);
    setName(pick.instrument_name ?? "");
    setQty("");
    setDone(null);
  }

  function clearSymbol() {
    setSymbol("");
    setName("");
    setQty("");
    setDone(null);
  }

  function fillMax() {
    if (side === "buy" && maxAffordable && maxAffordable > 0) setQty(String(maxAffordable));
    if (side === "sell" && held > 0) setQty(String(held));
    setDone(null);
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!valid) return;
    setDone(null);
    mutation.mutate(
      { side, symbol, quantity },
      {
        onSuccess: (ack) => {
          setDone(`${side === "buy" ? "Bought" : "Sold"} ${formatQty(ack.quantity)} ${ack.symbol}`);
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
        {/* Symbol: a search picker until one is chosen, then the live quote. */}
        <div className="flex flex-col gap-1.5">
          <span className="eyebrow">Symbol</span>
          {symbol === "" ? (
            <>
              <SymbolSearch onSelect={choose} placeholder="Search symbol or company…" />
              <p className="text-2xs text-fg-mute">Search by ticker or company name, e.g. AAPL, Reliance.</p>
            </>
          ) : (
            <ChosenSymbol
              symbol={symbol}
              name={name}
              price={price}
              loading={quote.isLoading}
              unavailable={quote.isError}
              onChange={clearSymbol}
            />
          )}
        </div>

        {/* Quantity, with a Max helper that fills the largest sensible size. */}
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <label htmlFor="trade-qty" className="eyebrow">
              Quantity
            </label>
            <button
              type="button"
              onClick={fillMax}
              disabled={side === "buy" ? !maxAffordable : held <= 0}
              className="font-mono text-2xs uppercase tracking-wider text-fg-mute hover:text-fg disabled:opacity-40"
            >
              Max{side === "buy" && maxAffordable ? ` ${formatQty(maxAffordable)}` : ""}
              {side === "sell" && held > 0 ? ` ${formatQty(held)}` : ""}
            </button>
          </div>
          <Input
            id="trade-qty"
            inputMode="decimal"
            placeholder="10"
            value={qty}
            onChange={(e) => {
              setQty(e.target.value.replace(/[^0-9.]/g, ""));
              setDone(null);
            }}
            invalid={mutation.isError || overCash || overHeld}
            mono
          />
        </div>

        {/* Order summary: cost vs cash on a buy, proceeds vs holding on a sell. */}
        {symbol !== "" && (
          <dl className="flex flex-col gap-1 border-t border-line pt-2 font-mono text-2xs">
            <SummaryRow
              label={side === "buy" ? "Est. cost" : "Est. proceeds"}
              value={orderValue !== null ? formatINR(orderValue) : "—"}
              tone={overCash ? "down" : undefined}
            />
            {side === "buy" ? (
              <SummaryRow label="Cash available" value={formatINR(cash)} />
            ) : (
              <SummaryRow label="You hold" value={`${formatQty(held)} ${symbol}`} />
            )}
          </dl>
        )}

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

      {overCash && (
        <p className="mt-2 font-mono text-2xs text-down">
          Order exceeds available cash ({formatINR(cash)}).
        </p>
      )}
      {overHeld && (
        <p className="mt-2 font-mono text-2xs text-down">
          You only hold {formatQty(held)} {symbol}.
        </p>
      )}
      {mutation.isError && (
        <p className="mt-2 break-words font-mono text-2xs text-down">
          {(mutation.error as ApiError).message}
        </p>
      )}
      {done && !mutation.isError && <p className="mt-2 font-mono text-2xs text-up">{done}</p>}
    </Panel>
  );
}

function ChosenSymbol({
  symbol,
  name,
  price,
  loading,
  unavailable,
  onChange,
}: {
  symbol: string;
  name: string;
  price: number | null;
  loading: boolean;
  unavailable: boolean;
  onChange: () => void;
}) {
  return (
    <div className="rounded border border-line-2 bg-panel-2 px-3 py-2">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <span className="font-mono text-sm text-fg">{symbol}</span>
          {name && <span className="ml-2 truncate text-2xs text-fg-dim">{name}</span>}
        </div>
        <button
          type="button"
          onClick={onChange}
          className="shrink-0 font-mono text-2xs uppercase tracking-wider text-fg-mute hover:text-fg"
        >
          Change
        </button>
      </div>
      <div className="mt-1 font-mono text-2xs">
        {loading ? (
          <span className="text-fg-mute">Fetching price…</span>
        ) : price !== null ? (
          <span className="text-fg-dim">
            Last <span className="text-fg tnum">{formatINR(price)}</span>
          </span>
        ) : unavailable ? (
          <span className="text-fg-mute">Live price unavailable — order fills at execution price.</span>
        ) : (
          <span className="text-fg-mute">—</span>
        )}
      </div>
    </div>
  );
}

function SummaryRow({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "down";
}) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-fg-mute">{label}</dt>
      <dd className={cn("tnum", tone === "down" ? "text-down" : "text-fg")}>{value}</dd>
    </div>
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
