# Prospera — Frontend Brief

> A self-contained brief for a frontend engineer to design and build the
> Prospera UI **autonomously**. You should be able to start without a meeting.
>
> **The backend already exists and is fully working.** Your job is the UI on top
> of it. This document + the live API docs are everything you need.

---

## 1. What Prospera is

Prospera is a **financial intelligence platform** (currently backend-only). It
lets a user:

- Run a **paper-trading portfolio** — virtual cash, buy/sell real stocks at real
  prices, track holdings and profit/loss.
- See **market data** — live quotes, historical price charts, company profiles.
- Read **news** and the **structured events** extracted from it.
- Get **AI-style intelligence** on any stock: a company health score, a
  price-move prediction, a fused **Buy/Hold/Sell** signal, and an **explainable
  bullish/bearish/neutral opinion with a written rationale**.
- **Backtest** — "if I had invested ₹100,000 in AAPL two years ago, what would it
  be worth?" with proper return/risk metrics.

**Everything is displayed in Indian Rupees (₹ / INR).**

---

## 2. Your goal

Design and build a clean, professional web dashboard on top of the existing REST
API. You own the visual design, component library, and page structure. This
brief gives you the product intent, the data available, and the constraints — not
pixel-level mockups.

---

## 3. The single most important resource: the live API contract

The backend is **FastAPI**, so the full API is auto-documented and typed.

1. **Run the backend** (see §8). Then open:
   - **`http://127.0.0.1:8000/docs`** — interactive Swagger UI. Every endpoint,
     with request/response schemas and a "Try it out" button. Live-explore here.
   - **`http://127.0.0.1:8000/redoc`** — the same, in a cleaner reading format.
   - **`http://127.0.0.1:8000/openapi.json`** — the machine-readable spec.
2. A snapshot of the spec is committed at **[`main/openapi.json`](main/openapi.json)**
   so you can generate a client before even running the backend.
3. **Generate a typed client** (recommended — do not hand-write fetch calls):
   ```bash
   npx openapi-typescript main/openapi.json -o src/api/schema.ts
   # or use orval / openapi-fetch for typed hooks
   ```
   Every request body and response is then fully typed in TypeScript.

Also useful: [`main/API_GUIDE.md`](main/API_GUIDE.md) has copy-paste request/
response examples, and [`GUIDE.md`](GUIDE.md) has a **glossary** of every finance
term (bullish, CAGR, XIRR, SIP, drawdown, …) if any are unfamiliar.

---

## 4. Recommended tech stack

Use what you're fastest in, but the project already assumes this stack (align
with it unless you have a strong reason not to):

- **Next.js + React + TypeScript**
- **Tailwind CSS + shadcn/ui** (components)
- **Recharts** (charts — price history, equity curves, score gauges)
- **TanStack Query** (data fetching/caching against the API)

---

## 5. Global constraints (read before designing)

| Constraint | What it means for the UI |
|-----------|--------------------------|
| **Currency is INR** | Format all money as `₹` with Indian grouping (e.g. ₹1,00,000). Never show USD. |
| **No authentication yet** | There is **no login/user system**. Don't design a login flow yet; assume a single local user. (An auth pass is planned later.) |
| **CORS is wide open** | The API allows all origins, so your dev frontend can call `http://127.0.0.1:8000` directly — no proxy needed. |
| **Base URL** | All endpoints are under `http://127.0.0.1:8000/api/v1/...` (plus `/health`). Make the base URL an env var. |
| **Some data needs a key** | Market-data & news endpoints need a Finnhub key configured in the backend `.env`. Without it they return a clear error — **design empty/error states**. The intelligence endpoints still return neutral results offline. |
| **Errors are consistent** | Errors come back as `{ "detail": "..." }` with HTTP 400/404/500. Surface `detail` in a toast/inline message. |
| **Not investment advice** | Wherever you show Buy/Sell/Bullish/Bearish, include a persistent **"Simulated — not investment advice"** disclaimer. |

---

## 6. Suggested screens (mapped to real endpoints)

Design freely, but here is a page structure that covers the product, with the
exact endpoints that feed each page. All paths are prefixed `/api/v1`.

### A. Portfolio Center (the paper-trading simulator)
The core interactive loop.

| Action | Endpoint |
|--------|----------|
| Create a portfolio ("environment") | `POST /environments/` `{name, owner_type:"user"}` |
| View a portfolio | `GET /environments/{id}` |
| Rename / delete | `PATCH` / `DELETE /environments/{id}` |
| Deposit / withdraw cash (INR) | `POST /portfolios/{id}/cash/deposit` · `/withdraw` |
| Buy / sell a stock | `POST /portfolios/{id}/buy` · `/sell` |
| Holdings | `GET /portfolios/{id}/holdings` |
| Transactions | `GET /portfolios/{id}/transactions` |
| Performance (value, P&L, return %) | `GET /portfolios/{id}/performance` |

> ⚠️ **Backend gap to coordinate:** there is currently **no "list all
> environments" endpoint** (only fetch-by-id). For now, persist created
> environment IDs client-side (localStorage). Flag to the backend owner if you
> want a `GET /environments` list — it's a small add.

### B. Market / Symbol Detail (the heart of the app)
A page for one stock (e.g. `/stocks/AAPL`). This is where the intelligence shines
— see §7 for the call order.

| Panel | Endpoint |
|-------|----------|
| Search symbols | `POST /market-data/search` `{query}` |
| Live quote | `GET /market-data/quote/{symbol}` |
| Price history chart | `GET /market-data/history/{symbol}?start_at=...&end_at=...&auto_sync=true` |
| Company profile | `GET /market-data/profile/{symbol}` |
| Company score (gauge) | `POST /company/analyze/{symbol}` then `GET /company/{symbol}` |
| Prediction (up/down) | `POST /predictions/predict/{symbol}` |
| Fused Buy/Hold/Sell | `POST /signals/fuse/{symbol}` |
| Explainable opinion | `POST /reasoning/analyze/{symbol}` |
| Recent events | `GET /events/company/{symbol}` |

### C. Intelligence Overview (rankings)
Dashboard-style lists across all analyzed symbols.

| Widget | Endpoint |
|--------|----------|
| Ranked company scores | `GET /company/` |
| Latest predictions | `GET /predictions/` |
| Latest fused signals | `GET /signals/` |
| Latest opinions | `GET /reasoning/` |

### D. News Center
| Panel | Endpoint |
|-------|----------|
| Global / India feeds | `GET /news/global` · `/news/india` |
| Company / sector news | `GET /news/company/{symbol}` · `/news/sector/{sector}` |
| Search/filter warehouse | `GET /news/articles?category=&symbol=&query=` |
| Warehouse stats | `GET /news/warehouse/stats` |
| Trigger a sync (admin) | `POST /news/sync` |
| Structured events | `GET /events`, `GET /events/stats` |

### E. Research Workspace (document Q&A / RAG)
| Action | Endpoint |
|--------|----------|
| Upload/ingest a document | `POST /research/documents` `{title, content, document_type, symbols}` |
| Semantic search | `POST /research/search` `{query, top_k}` → ranked passages with scores |
| List documents / stats | `GET /research/documents` · `/research/stats` |

### F. Backtesting ("what if I had invested…")
A form + a results view with an **equity-curve chart** and a metrics grid.

| Action | Endpoint |
|--------|----------|
| Lump-sum simulation | `POST /backtest/lumpsum` `{symbol, amount, start_at, end_at}` |
| Monthly SIP simulation | `POST /backtest/sip` `{symbol, monthly_amount, start_at, end_at}` |

Response includes: `total_invested`, `final_value`, `profit`, `total_return_pct`,
`cagr_pct`, `xirr_pct`, `annualized_volatility_pct`, `sharpe_ratio`,
`sortino_ratio`, `max_drawdown_pct`, and a `curve[]` of `{on, invested, value}`
points to plot (invested vs. value over time).

---

## 7. The intelligence pipeline (important UX detail)

On a symbol-detail page, a full recommendation is produced by **four stored
stages that feed each other**. To show a complete, consistent picture, trigger
them in this order (each is a `POST` that computes and stores, then you can `GET`):

```
1) POST /company/analyze/{symbol}      → company score (growth/risk/sentiment)
2) POST /predictions/predict/{symbol}  → next-move forecast
3) POST /signals/fuse/{symbol}         → blends 1 + 2 + events → Buy/Hold/Sell
4) POST /reasoning/analyze/{symbol}    → bullish/bearish/neutral + written explanation
```

UX suggestion: an **"Analyze" button** that runs all four (with a loading state),
then renders the score gauge, the prediction, the Buy/Hold/Sell badge, and the
reasoning paragraph with its "drivers" list. The reasoning response also includes
`citations` (research snippets) and a `confidence` (0–1) you can show as a meter.

> If you'd prefer a single call that runs the whole pipeline, ask the backend
> owner for an aggregate endpoint — it's a straightforward add.

---

## 8. Running the backend locally (so you can develop against it)

From the repo root (needs Python 3.11):

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
cd main
python main.py --reload
```

Backend is now at `http://127.0.0.1:8000` (docs at `/docs`). It runs **offline**
on a local SQLite file with no config. To get live quotes/news, the backend owner
adds a free Finnhub key to `main/.env` (`MARKET_DATA_API_KEY=...`) — but you can
build and style everything else without it.

Full setup details and a glossary: **[GUIDE.md](GUIDE.md)**.

---

## 9. Suggested build order (MVP first)

1. **Skeleton + API client** — layout shell (sidebar/nav), typed client from
   `openapi.json`, TanStack Query set up, `/health` check.
2. **Portfolio Center** — create env, deposit cash, buy/sell, holdings +
   performance. This is the most tangible loop and uses no AI.
3. **Symbol Detail** — quote + price chart + profile.
4. **Intelligence** — the "Analyze" flow (§7): score gauge, prediction, signal
   badge, reasoning card.
5. **Backtesting** — form + equity-curve chart + metrics grid.
6. **News + Research + Events** — feeds, search, ingest.

---

## 10. Design notes & open questions to raise

- **Empty/error/loading states matter** — several data sources depend on a key or
  on prior analysis existing. Design "not analyzed yet", "needs API key", and
  "no data in this window" states deliberately.
- **Number formatting** — INR grouping, signed percentages (green/red), and
  compact large numbers (e.g. ₹2.85L cr market cap).
- **Backtest date windows** — the backend's history sync appends forward; picking
  an older window after a newer one was fetched can return "not enough history".
  Prefer recent windows in demos, and surface the backend's error cleanly.
- **Ask the backend owner about:** (a) a `GET /environments` list endpoint,
  (b) an aggregate "analyze everything for this symbol" endpoint, (c) when auth /
  multi-user is coming (affects whether you build account UI now).

---

*Everything here is backed by the live spec at `/openapi.json`
([snapshot](main/openapi.json)). When in doubt, trust the spec — it is generated
from the running code and is always current.*
