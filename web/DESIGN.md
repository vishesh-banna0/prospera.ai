# Prospera — Design System

> The reasoning behind every visual decision, written for someone new to
> frontend who has to maintain this later. Read this before changing tokens.

## The thesis

**Prospera is an instrument, not a product page.** It is the console of a
machine that watches markets and forms opinions about them, in rupees. So the
interface is built like a piece of precision measurement equipment: dense,
quiet, calibrated, and trustworthy. There is no marketing surface anywhere. It
opens on data.

Two ideas drive everything below:

1. **The only color is direction.** The entire chrome — background, panels,
   borders, text, buttons, nav — is colorless graphite. The *only* chromatic
   colors in normal use are the ones that mean something about the market:
   green for up/buy/bullish, red for down/sell/bearish, slate for
   neutral/hold. When you see color in Prospera, it is the market talking, never
   the UI decorating itself. This is why a single glowing "brand accent" (the
   default AI-dashboard move) is deliberately absent.
2. **The machine's numbers all wear the same instrument.** Every bounded reading
   the machine produces — a company score (0–100), a probability (0–1), a
   confidence (0–1), a signal strength — is drawn as one calibrated gauge with
   real tick marks. Scanning the app, "how strong / how sure" always reads the
   same way. That gauge is the signature (§5).

## 1. Color

Dark, cool graphite. Not pure black (pure black is a void; instruments are
machined metal). Not the near-black-plus-one-acid-accent look that every AI
dashboard ships — the restraint here is that chrome has *no* accent at all.

| Token | Hex | Role |
|-------|-----|------|
| `--ink` | `#0D0F13` | app background (cool graphite, blue undertone) |
| `--panel` | `#14171D` | raised panel surface |
| `--panel-2` | `#1B1F27` | inputs, higher surfaces, selected rows |
| `--line` | `#262B34` | hairline borders (visible but quiet) |
| `--line-2` | `#333B47` | stronger dividers, gauge ticks |
| `--fg` | `#E7EBF1` | primary text (cool white, never pure #FFF) |
| `--fg-dim` | `#98A2B1` | secondary text |
| `--fg-mute` | `#5F6875` | labels, captions, axis ticks |

**Data direction — the only chromatic colors:**

| Token | Hex | Meaning |
|-------|-----|---------|
| `--up` | `#2FBE8A` | gain · buy · bullish (emerald, blue-shifted) |
| `--down` | `#E85A45` | loss · sell · bearish (vermilion, orange-shifted) |
| `--hold` | `#8B94A2` | neutral · hold (slate) |

**Semantic (used sparingly, never for market direction):**

| Token | Hex | Role |
|-------|-----|------|
| `--warn` | `#E0A038` | caution — "needs API key", degraded states |
| `--ring` | `#C6D2E2` | keyboard focus ring (cool near-white, high contrast) |

**Why green/red at all, and why these greens/reds?** Money has a hundred-year
convention: green up, red down. Fighting it to look clever would make the
instrument *harder* to read, which is the opposite of the job. But the two hues
are chosen to survive red-green color blindness: `--up` is pushed toward blue
(emerald) and `--down` toward orange (vermilion), so they differ in *hue family
and lightness*, not just red-vs-green. And direction is **never** encoded by hue
alone — every signed value also carries a sign (`+`/`−`), a glyph (▲/▼), and
position. Three redundant cues; the color is the fourth.

Focus ring is colorless on purpose: it belongs to the chrome, not the data.

## 2. Type — three roles, contrasted by width

Most of this app is numbers, so the type system is chosen around legible figures
first and personality second.

| Role | Face | Why |
|------|------|-----|
| **Display** | **Archivo** (600–700) | A sturdy, slightly wide grotesque. Used *only* for display — page titles, the wordmark, and tracked-out uppercase eyebrows — where the tracking gives it the character of an engraved instrument-panel label. Restraint is the point; it never carries prose. |
| **Body / UI** | **IBM Plex Sans** (400–600) | Engineered by IBM for exactly this "human + machine" register. Humane but technical, and dense-friendly at small sizes where a dashboard lives. |
| **Data** | **IBM Plex Mono** (400–600) | The load-bearing face. Every number goes here — genuine tabular figures by construction, so live quotes never jitter as digits change. Mono money also *reads as a ledger / contract note*, which is the right instrument metaphor. |

Three distinct faces with three distinct jobs. A reader can tell "label vs.
prose vs. number" by shape alone before reading a word. (First plan reached for
Archivo *Expanded* for a literal width contrast; `next/font/google` doesn't ship
that as a separate family, so the width idea is carried by tracked uppercase on
Archivo instead — a smaller, honest adjustment that keeps the engraved-label
character.)

**`font-variant-numeric: tabular-nums` is on for every numeric context**, mono or
not. A number that changes width when a digit changes is a bug in the type
system.

Type scale (rem, 1rem = 16px): `0.6875` (11, micro eyebrow) · `0.75` (12) ·
`0.8125` (13, dense UI default) · `0.875` (14, body) · `1` (16) · `1.25` (20) ·
`1.75` (28) · `2.5` (40) · `3.5` (56, hero readout). Line-height tight on
figures (1.05–1.15), comfortable on prose (1.5).

## 3. The rupee, as a first-class material

This app thinks in **lakhs and crores**, and that is the single most specific
thing in the brief. It is built into the type system, not bolted on at render
time. One shared formatter module (`src/lib/money.ts`) owns all of it; nothing
else is allowed to call `toFixed` on money.

- **Full grouping is Indian:** `₹1,00,000`, `₹1,23,45,678` (via `en-IN`
  `Intl.NumberFormat`), never Western `₹100,000`.
- **Compact is lakh/crore:** `₹2.85 Cr`, `₹84.20 L`, and for market caps,
  `₹2.85L cr` (lakh-crore). The compaction ladder is K → L (lakh, 1e5) →
  Cr (crore, 1e7) → L cr (lakh-crore, 1e12).
- Money is rendered in the mono data face so grouping commas line up down a
  column like a printed statement.

## 4. Layout — a cockpit, not a page

Density over air. Whitespace is *earned*, not sprayed. The shell is a fixed
instrument frame; content scrolls inside it.

```
┌─────────────────────────────────────────────────────────────────────────┐
│ PROSPERA  ·instrument      ● live   NSE·15:42   ₹INR    [ SIMULATED — NIA ]│  status strip
├──────────┬──────────────────────────────────────────────────────────────┤
│ PORTFOLIO│  eyebrow: SECTION                                              │
│ MARKETS  │  ┌── panel ─────────────────┐  ┌── panel ───────────────────┐  │
│ INTEL    │  │ NET LIQUIDATION          │  │ CONFIDENCE                  │  │
│ BACKTEST │  │ ₹1,24,58,300             │  │ ├──┼──┼──╫──┼──┼──┤  0.72     │  │  ← the gauge
│ NEWS     │  │ +₹3,20,110  ▲ 2.64%      │  │ low        high             │  │
│ RESEARCH │  └──────────────────────────┘  └─────────────────────────────┘  │
│          │  ┌── table (mono, tabular) ────────────────────────────────┐   │
│  ─────   │  │ SYMBOL   LAST       CHG        QTY      VALUE            │   │
│  health  │  │ RELIANCE 2,945.60   ▲ 1.20%    120      ₹3,53,472        │   │
│          │  └──────────────────────────────────────────────────────────┘  │
└──────────┴──────────────────────────────────────────────────────────────┘
```

- **Status strip (top):** the instrument's status bar — API health (a live dot),
  market clock, base currency (₹ INR), and the **"Simulated — not investment
  advice"** plate. That disclaimer is a permanent etched part of the frame, not a
  footer, because machine opinion is always labelled as machine opinion.
- **Left rail:** dense, uppercase, tracked labels (engraved-panel feel). Active
  item marked by a fill + a hard left marker bar, not by a colored glow.
- **Panels:** hairline `--line` borders, a small tracked-uppercase eyebrow label
  per panel, generous internal grid. Corners are barely rounded (3px) — machined,
  not pill-soft, and never the shadcn `rounded-2xl`.

## 5. Signature — the calibrated gauge

**One element, and everything else stays quiet around it.**

Every bounded reading the machine emits is drawn as the same instrument: a
horizontal graduated track with fine minor ticks and bolder major ticks, a
filled portion up to the reading, and a precise marker line with the value in
mono. It renders a company score (0–100), a prediction probability (0–1), a
confidence (0–1), and a fused-signal strength — all as *the same shape at
different scales*, so "how strong / how sure" reads identically everywhere.

The fill color is the only place the gauge takes a data color: green when the
reading is bullish/strong, red when bearish/weak, slate when neutral. The
confidence gauge specifically is slate (confidence is not directional — you can
be very confident in a Sell).

**Why this belongs to *this* brief:** Prospera's whole differentiator is
*explainable, always-labelled machine opinion*. Confidence is attached to the
prediction, the signal, and the reasoning — it is the most-repeated primitive in
the product. Building it as a real measuring instrument (not a progress bar)
makes the thesis — "an instrument you trust with money" — literally true, and it
is the through-line that ties four separate intelligence endpoints into one
readable picture.

**Where the motion budget goes:** the gauge is also the payoff of the *Analyze*
sequence (four backend stages that feed each other: score → prediction → fused
signal → reasoning). That screen choreographs several gauges settling to their
readings in stage order — one orchestrated event, each stage landing as it
resolves and visibly feeding the next. Everywhere else, motion is near-invisible:
numbers count once on mount, charts draw once and hold still, nothing idles or
pulses. All of it is disabled under `prefers-reduced-motion`.

---

## 6. Self-critique — where the first plan was a default, and what changed

The rule: for palette, type, layout, and signature, ask "would I have produced
this for *any* fintech dashboard?" Where yes, revise.

- **Chrome accent → removed entirely.** First pass gave the chrome an
  iris/violet interactive accent. That is the reflexive AI-SaaS move and it
  competes with the market colors for attention. Revised to *no chrome accent
  at all* — "the only color is direction." This is more disciplined, more
  specific to a money instrument, and makes the green/red feel earned instead of
  decorative. This is the plan's sharpest anti-default decision.
- **Direction colors → tuned toward money convention, away from a trend pair.**
  First pass reached for teal/amber (the fashionable "modern fintech" pair).
  Revised to emerald-green / vermilion-red: it honors the ingrained green-up /
  red-down reading a money user has, while the blue-shift / orange-shift plus the
  mandatory sign+glyph keep it color-blind safe. Amber was demoted to a pure
  *caution* semantic (needs-key states), never a direction.
- **Display face → chosen for width contrast, not mood.** The easy pick was
  Space Grotesk (now an AI-design tell) or plain Inter (the shadcn factory
  default). Revised to Archivo *Expanded* so the display role is distinguished
  from body and data by **width**, giving three visibly different type shapes
  without a third personality — and Plex Sans/Mono ground the "machine console"
  metaphor better than Inter.
- **Signature → elevated from "a confidence widget" to a system.** The brief
  itself lists "confidence meter as an instrument" as a candidate, so shipping
  exactly that would be taking the suggestion. Revised so the *same* gauge form
  renders every bounded reading (score, probability, confidence, signal), making
  it a system-level identity — one instrument you learn once and read
  everywhere — rather than a single decorated bar.
- **Kept, and defended, not defaulted:** dark theme (a cockpit watched all day is
  dark for real ergonomic reasons, stated as a choice), and green/red for
  gains/losses (a domain convention, not an AI cliché, and made intentional by
  the colorless chrome around it).

## 7. Library notes (for the maintainer)

- **Tailwind v3** with tokens as CSS variables mapped to semantic class names
  (`bg-panel`, `text-up`, `border-line`). The variables live in `globals.css`;
  the names live in `tailwind.config.ts`. Change a hex in one place.
- **Recharts** for the equity curve and price history (the load-bearing
  visuals): it renders SVG we can style to tokens and handles responsive sizing.
  The gauge is *hand-built SVG*, not Recharts — it needs exact tick geometry a
  charting lib won't give cleanly.
- **TanStack Query** owns all server state (caching, loading, error). Components
  never fetch directly.
- **Typed client generated** from `main/openapi.json` into `src/api/schema.ts`
  (`openapi-typescript`). Response types are never hand-written — when the
  backend changes, regenerate.
- **One error surface.** The backend returns `{ "detail": "..." }`; we surface
  `detail` verbatim everywhere because the backend's messages are specific.
