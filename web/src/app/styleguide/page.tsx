"use client";

import { useState } from "react";
import { Gauge } from "@/components/ui/Gauge";
import { SignedNumber } from "@/components/ui/SignedNumber";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input, Field } from "@/components/ui/Input";
import { Panel, Stat } from "@/components/ui/Panel";
import { Skeleton, StatSkeleton, TableSkeleton } from "@/components/ui/Skeleton";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { IconGaugeEmpty, IconKey, IconWindow } from "@/components/ui/icons";
import { EquityCurve } from "@/components/charts/EquityCurve";
import { sampleEquityCurve } from "./sample";
import {
  formatCompactINR,
  formatINR,
  formatQty,
  formatRatioPct,
} from "@/lib/money";

export default function StyleguidePage() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6">
      <header className="mb-8 border-b border-line pb-5">
        <p className="eyebrow">System · Styleguide</p>
        <h1 className="mt-2 font-display text-2xl font-bold tracking-tight text-fg">
          The instrument, disassembled
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-fg-dim">
          Every token and component the product is built from. The rule that runs
          through all of it: the chrome is colorless graphite, and the only
          chromatic color is the market&rsquo;s direction. See{" "}
          <span className="font-mono text-fg">DESIGN.md</span> for the reasoning.
        </p>
      </header>

      <div className="flex flex-col gap-10">
        <ColorSection />
        <TypeSection />
        <RupeeSection />
        <GaugeSection />
        <SignedSection />
        <ControlsSection />
        <BadgeSection />
        <ChartSection />
        <LoadingSection />
        <EmptyStatesSection />
      </div>

      <footer className="mt-12 border-t border-line pt-4 font-mono text-2xs text-fg-mute">
        Prospera · instrument · every figure simulated · not investment advice
      </footer>
    </div>
  );
}

/* ---- section frame ------------------------------------------------------- */

function Section({
  n,
  title,
  note,
  children,
}: {
  n: string;
  title: string;
  note?: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <div className="mb-3 flex items-baseline gap-3">
        <span className="font-mono text-2xs text-fg-mute tnum">{n}</span>
        <h2 className="font-display text-sm font-semibold uppercase tracking-[0.12em] text-fg">
          {title}
        </h2>
      </div>
      {note && <p className="mb-4 max-w-2xl text-2xs leading-relaxed text-fg-dim">{note}</p>}
      {children}
    </section>
  );
}

/* ---- 01 color ------------------------------------------------------------ */

const CHROME = [
  ["--ink", "#0D0F13", "app background"],
  ["--panel", "#14171D", "raised panel"],
  ["--panel-2", "#1B1F27", "input / higher surface"],
  ["--line", "#262B34", "hairline border"],
  ["--line-2", "#333B47", "divider / ticks"],
  ["--fg", "#E7EBF1", "primary text"],
  ["--fg-dim", "#98A2B1", "secondary text"],
  ["--fg-mute", "#5F6875", "labels / captions"],
] as const;

const DATA = [
  ["--up", "#2FBE8A", "gain · buy · bullish"],
  ["--down", "#E85A45", "loss · sell · bearish"],
  ["--hold", "#8B94A2", "neutral · hold"],
  ["--warn", "#E0A038", "caution (needs key)"],
  ["--ring", "#C6D2E2", "focus ring"],
] as const;

function ColorSection() {
  return (
    <Section
      n="01"
      title="Color"
      note="Chrome is eight graphite steps with no accent. The only chromatic colors are the three that mean something about the market, plus a caution amber and a focus ring. If you see color in the product, it's the data talking."
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <SwatchGroup label="Chrome — graphite, no accent" rows={CHROME} />
        <SwatchGroup label="Data — the only chromatic colors" rows={DATA} />
      </div>
    </Section>
  );
}

function SwatchGroup({
  label,
  rows,
}: {
  label: string;
  rows: ReadonlyArray<readonly [string, string, string]>;
}) {
  return (
    <Panel label={label} bodyClassName="p-0">
      <ul>
        {rows.map(([token, hex, role]) => (
          <li
            key={token}
            className="flex items-center gap-3 border-b border-line px-3 py-2 last:border-b-0"
          >
            <span
              className="h-6 w-6 shrink-0 rounded-sm border border-line-2"
              style={{ background: hex }}
              aria-hidden
            />
            <span className="w-28 font-mono text-2xs text-fg tnum">{token}</span>
            <span className="w-16 font-mono text-2xs text-fg-dim tnum">{hex}</span>
            <span className="text-2xs text-fg-mute">{role}</span>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

/* ---- 02 type ------------------------------------------------------------- */

// Full class strings (not `text-${name}`) so Tailwind's scanner keeps them.
const SCALE: ReadonlyArray<readonly [string, string, string, string]> = [
  ["3xl", "3.5rem / 56", "hero readout", "text-3xl"],
  ["2xl", "2.5rem / 40", "page figure", "text-2xl"],
  ["xl", "1.75rem / 28", "panel figure", "text-xl"],
  ["lg", "1.25rem / 20", "sub-figure", "text-lg"],
  ["base", "1rem / 16", "emphasis body", "text-base"],
  ["sm", "0.875rem / 14", "body", "text-sm"],
  ["xs", "0.8125rem / 13", "dense UI (default)", "text-xs"],
  ["2xs", "0.75rem / 12", "captions", "text-2xs"],
  ["micro", "0.6875rem / 11", "eyebrow", "text-micro"],
];

function TypeSection() {
  return (
    <Section
      n="02"
      title="Type — three roles"
      note="Display (Archivo) is used with restraint, in tracked uppercase. Body (IBM Plex Sans) carries prose and UI. Data (IBM Plex Mono) carries every number, with tabular figures so digits never shift width. You can tell label from prose from number by shape alone."
    >
      <div className="grid gap-4 lg:grid-cols-3">
        <Panel label="Display · Archivo">
          <p className="font-display text-2xl font-bold text-fg">Prospera</p>
          <p className="eyebrow mt-3">Engraved panel label</p>
          <p className="mt-1 text-2xs text-fg-mute">Titles, wordmark, eyebrows. Restraint.</p>
        </Panel>
        <Panel label="Body · IBM Plex Sans">
          <p className="text-sm text-fg">
            The console of a machine that watches markets and forms opinions.
          </p>
          <p className="mt-2 text-xs text-fg-dim">
            Humane but technical — built for dense UI at small sizes.
          </p>
        </Panel>
        <Panel label="Data · IBM Plex Mono">
          <p className="font-mono text-xl text-fg tnum">₹1,23,45,678.00</p>
          <p className="font-mono text-sm text-fg-dim tnum">2,945.60 · 120 · 0.72</p>
          <p className="mt-2 text-2xs text-fg-mute">Tabular figures. Ledger alignment.</p>
        </Panel>
      </div>

      <Panel label="Type scale" className="mt-4">
        <ul className="flex flex-col divide-y divide-line">
          {SCALE.map(([name, size, use, cls]) => (
            <li key={name} className="flex items-baseline gap-4 py-2">
              <span className="w-12 shrink-0 font-mono text-2xs text-fg-mute">{name}</span>
              <span className="w-28 shrink-0 font-mono text-2xs text-fg-dim tnum">{size}</span>
              <span className="hidden w-32 shrink-0 text-2xs text-fg-mute sm:block">{use}</span>
              <span className={`truncate text-fg ${cls}`}>Growth · 24.6%</span>
            </li>
          ))}
        </ul>
      </Panel>
    </Section>
  );
}

/* ---- 03 rupee ------------------------------------------------------------ */

const AMOUNTS = [920, 100000, 1234567.89, 8420000, 2.85e12];

function RupeeSection() {
  return (
    <Section
      n="03"
      title="The rupee, as a material"
      note="One formatter module owns all of it. Full amounts use Indian grouping (lakh/crore rhythm). Compact climbs the K → L → Cr → L cr ladder. Nothing else in the app calls toFixed on money."
    >
      <Panel label="formatINR · formatCompactINR" bodyClassName="p-0">
        <div className="overflow-x-auto">
        <div className="grid min-w-[22rem] grid-cols-[1fr_auto_auto] gap-x-6 gap-y-0 px-3 py-1 text-xs">
          <div className="border-b border-line py-2 font-mono text-2xs uppercase tracking-wider text-fg-mute">
            raw value
          </div>
          <div className="border-b border-line py-2 text-right font-mono text-2xs uppercase tracking-wider text-fg-mute">
            full · grouped
          </div>
          <div className="border-b border-line py-2 text-right font-mono text-2xs uppercase tracking-wider text-fg-mute">
            compact
          </div>
          {AMOUNTS.map((v) => (
            <RupeeRow key={v} value={v} />
          ))}
        </div>
        </div>
      </Panel>
      <p className="mt-2 font-mono text-2xs text-fg-mute">
        market cap example → {formatCompactINR(2.85e12)} · quantity →{" "}
        {formatQty(120.5)} · ratio → {formatRatioPct(0.72)}
      </p>
    </Section>
  );
}

function RupeeRow({ value }: { value: number }) {
  return (
    <>
      <div className="border-b border-line py-2 font-mono text-fg-dim tnum">{value}</div>
      <div className="border-b border-line py-2 text-right font-mono text-fg tnum">
        {formatINR(value)}
      </div>
      <div className="border-b border-line py-2 text-right font-mono text-fg tnum">
        {formatCompactINR(value)}
      </div>
    </>
  );
}

/* ---- 04 gauge (signature) ------------------------------------------------ */

function GaugeSection() {
  return (
    <Section
      n="04"
      title="Signature — the calibrated gauge"
      note="One instrument for every bounded machine reading. A digital readout over an analog graduated track, like a multimeter. The same shape renders a 0–100 score and a 0–1 confidence. The fill color is the only place it takes a data color; confidence is slate because you can be very sure of a Sell."
    >
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Panel label="Company score">
          <Gauge
            value={78}
            min={0}
            max={100}
            tone="up"
            readout="78"
            label="Overall"
            caption={["0", "100"]}
            ariaLabel="Company score 78 of 100"
          />
        </Panel>
        <Panel label="Risk score">
          <Gauge
            value={34}
            min={0}
            max={100}
            tone="down"
            readout="34"
            label="Risk"
            caption={["low", "high"]}
            ariaLabel="Risk score 34 of 100"
          />
        </Panel>
        <Panel label="Prediction">
          <Gauge
            value={0.61}
            min={0}
            max={1}
            tone="up"
            readout="0.61"
            label="P(up)"
            caption={["0.0", "1.0"]}
            ariaLabel="Probability of up move 0.61"
          />
        </Panel>
        <Panel label="Confidence">
          <Gauge
            value={0.72}
            min={0}
            max={1}
            tone="hold"
            readout="0.72"
            label="Confidence"
            caption={["low", "high"]}
            ariaLabel="Confidence 0.72 of 1"
          />
        </Panel>
      </div>
    </Section>
  );
}

/* ---- 05 signed numbers --------------------------------------------------- */

function SignedSection() {
  return (
    <Section
      n="05"
      title="Signed numbers"
      note="Direction is encoded four ways at once — glyph, sign, color, and position in a column — so it survives color blindness and greyscale. Never color alone."
    >
      <Panel bodyClassName="p-0">
        <div className="overflow-x-auto">
        <table className="w-full min-w-[30rem] text-xs">
          <thead>
            <tr className="border-b border-line text-left font-mono text-2xs uppercase tracking-wider text-fg-mute">
              <th className="px-3 py-2 font-normal">Symbol</th>
              <th className="px-3 py-2 text-right font-normal">Last</th>
              <th className="px-3 py-2 text-right font-normal">Day change</th>
              <th className="px-3 py-2 text-right font-normal">Unrealized</th>
            </tr>
          </thead>
          <tbody className="font-mono tnum">
            {[
              ["RELIANCE", 2945.6, 1.2, 41230],
              ["TCS", 3821.1, -0.64, -8850],
              ["HDFCBANK", 1642.0, 0.0, 0],
            ].map(([sym, last, chg, pnl]) => (
              <tr key={sym as string} className="border-b border-line last:border-0">
                <td className="px-3 py-2 text-fg">{sym}</td>
                <td className="px-3 py-2 text-right text-fg">{formatINR(last as number)}</td>
                <td className="px-3 py-2 text-right">
                  <SignedNumber value={chg as number} kind="pct" />
                </td>
                <td className="px-3 py-2 text-right">
                  <SignedNumber value={pnl as number} kind="inr" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      </Panel>
    </Section>
  );
}

/* ---- 06 controls --------------------------------------------------------- */

function ControlsSection() {
  const [amount, setAmount] = useState("100000");
  return (
    <Section
      n="06"
      title="Controls"
      note="The primary action is high-contrast, not a colored brand button — chrome stays colorless. Buy/Sell are the one place a control speaks in market color, because a trade genuinely has a direction. Focus is a colorless ring (tab through to see it)."
    >
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel label="Buttons">
          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <Button variant="primary">Deposit cash</Button>
              <Button variant="secondary">Cancel</Button>
              <Button variant="ghost">Details</Button>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Button variant="buy">Buy</Button>
              <Button variant="sell">Sell</Button>
              <Button variant="primary" loading>
                Analyzing
              </Button>
              <Button variant="secondary" disabled>
                Disabled
              </Button>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Button size="sm" variant="secondary">
                Small
              </Button>
              <Button size="md" variant="secondary">
                Medium
              </Button>
              <Button size="lg" variant="secondary">
                Large
              </Button>
            </div>
          </div>
        </Panel>
        <Panel label="Inputs">
          <div className="flex flex-col gap-3">
            <Field label="Amount (₹)" htmlFor="sg-amount" hint="Indian grouping applies on submit.">
              <Input
                id="sg-amount"
                value={amount}
                inputMode="numeric"
                onChange={(e) => setAmount(e.target.value)}
                mono
              />
            </Field>
            <Field label="Symbol" htmlFor="sg-sym">
              <Input id="sg-sym" placeholder="e.g. RELIANCE" defaultValue="" />
            </Field>
            <Field label="Monthly SIP" htmlFor="sg-bad" error="Enter an amount of at least ₹500.">
              <Input id="sg-bad" defaultValue="0" invalid mono />
            </Field>
          </div>
        </Panel>
      </div>
    </Section>
  );
}

/* ---- 07 badges ----------------------------------------------------------- */

function BadgeSection() {
  return (
    <Section
      n="07"
      title="Verdict badges"
      note="Machine opinion — Buy/Hold/Sell and bullish/bearish/neutral — always labelled as such and carried by a word plus a tick mark, not color alone."
    >
      <Panel>
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="up">Buy</Badge>
          <Badge tone="hold">Hold</Badge>
          <Badge tone="down">Sell</Badge>
          <Badge tone="up">Bullish</Badge>
          <Badge tone="down">Bearish</Badge>
          <Badge tone="hold">Neutral</Badge>
          <Badge tone="neutral">Rating A</Badge>
          <Badge tone="warn">Needs key</Badge>
        </div>
      </Panel>
    </Section>
  );
}

/* ---- 08 chart ------------------------------------------------------------ */

function ChartSection() {
  const data = sampleEquityCurve();
  return (
    <Section
      n="08"
      title="Equity curve"
      note="The backtest's load-bearing visual. Value is the emphasized line; invested is the quiet dashed baseline; the widening gap between them is the whole story. Fill color is the market's verdict. Hover a point for the readout."
    >
      <Panel
        label="Invested vs value"
        aside={
          <span className="font-mono text-2xs uppercase tracking-wider text-fg-mute">
            sample data — demo
          </span>
        }
      >
        <EquityCurve data={data} />
        <div className="mt-3 flex items-center gap-4 font-mono text-2xs text-fg-mute">
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-0.5 w-4 bg-up" /> value
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-0 w-4 border-t border-dashed border-fg-mute" /> invested
          </span>
        </div>
      </Panel>
    </Section>
  );
}

/* ---- 09 loading ---------------------------------------------------------- */

function LoadingSection() {
  return (
    <Section
      n="09"
      title="Loading"
      note="Skeletons mirror the shape of the readout they stand in for, so the layout doesn't jump when data lands. The pulse stops under reduced-motion."
    >
      <div className="grid gap-4 sm:grid-cols-3">
        <Panel label="Figure">
          <StatSkeleton />
        </Panel>
        <Panel label="Populated (for contrast)">
          <Stat label="Net liquidation" value={formatINR(12458300, 0)} sub="settled" />
        </Panel>
        <Panel label="Table">
          <TableSkeleton rows={4} />
        </Panel>
      </div>
      <div className="mt-4">
        <Panel label="Primitive">
          <div className="flex flex-col gap-2">
            <Skeleton className="h-3 w-1/3" />
            <Skeleton className="h-3 w-2/3" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </Panel>
      </div>
    </Section>
  );
}

/* ---- 10 empty + error states --------------------------------------------- */

function EmptyStatesSection() {
  return (
    <Section
      n="10"
      title="Empty & fault states"
      note="Three empty states that must read differently — an invitation, a missing-key notice, an out-of-range notice — plus the one error surface, which shows the backend's message verbatim."
    >
      <div className="grid gap-4 lg:grid-cols-3">
        <EmptyState
          icon={<IconGaugeEmpty />}
          title="Not analyzed yet"
          action={<Button variant="primary" size="sm">Run analysis</Button>}
        >
          The machine hasn&rsquo;t formed an opinion on this symbol. Run the four
          stages — score, prediction, signal, reasoning — to see its read.
        </EmptyState>

        <EmptyState icon={<IconKey />} title="Market data needs a key" tone="warn">
          Live quotes and news need a Finnhub key in the backend. Intelligence,
          backtests, and the portfolio still work without one.
        </EmptyState>

        <EmptyState icon={<IconWindow />} title="No data in this window">
          There aren&rsquo;t enough price bars for this range. Try a more recent
          window — history is appended forward.
        </EmptyState>
      </div>

      <div className="mt-4">
        <ErrorState
          detail="Symbol 'RELXNCE' not found. Search for a valid symbol first."
          onRetry={() => undefined}
        />
      </div>
    </Section>
  );
}
