# Prospera — The Complete Newcomer's Guide

> Read this first. It assumes **no prior web-development or Python-web
> experience**. If you can open a terminal and copy-paste commands, you can run
> and understand this project.

This guide has three jobs:

1. **Get the backend running on your machine** in a few minutes.
2. **Explain every tool** we use, in plain English (so unfamiliar names stop
   being scary).
3. **Teach you how to read the codebase** — where to click first, how a request
   flows through the system, and how to add your own feature.

There is **no frontend** yet (by design). Everything is a *backend*: a program
that listens for requests and answers with data (JSON). You interact with it
through an auto-generated web page of buttons (`/docs`), `curl`, or any script.

---

## Table of contents

1. [The 60-second pitch](#1-the-60-second-pitch)
2. [Run it in 5 minutes](#2-run-it-in-5-minutes)
3. [Every tool, explained plainly](#3-every-tool-explained-plainly)
4. [The mental model: how a request flows](#4-the-mental-model-how-a-request-flows)
5. [How the code is organized](#5-how-the-code-is-organized)
6. [A guided tour — read the code in this order](#6-a-guided-tour--read-the-code-in-this-order)
7. [The modules, one by one](#7-the-modules-one-by-one)
8. [How money and currency work (INR)](#8-how-money-and-currency-work-inr)
9. [Using the AI features (your local Llama)](#9-using-the-ai-features-your-local-llama)
10. [How to add a new feature (recipe)](#10-how-to-add-a-new-feature-recipe)
11. [Testing, linting, and CI](#11-testing-linting-and-ci)
12. [Everyday git workflow](#12-everyday-git-workflow)
13. [Troubleshooting](#13-troubleshooting)
14. [Glossary (finance + tech words)](#14-glossary-finance--tech-words)

---

## 1. The 60-second pitch

Prospera is a **financial intelligence backend**. Today it can:

- **Simulate a portfolio** — create a virtual wallet, add fake cash, buy/sell
  real stocks at real prices, and track your profit/loss (paper trading).
- **Fetch market data** — live quotes, historical prices, company profiles,
  from one internal gateway so the rest of the app never talks to outside
  providers directly.
- **Collect news** — pull financial news, clean it, classify it, de-duplicate
  it, and store it.
- **Turn news into structured events** — e.g. "NVIDIA beat earnings" becomes a
  queryable record with sentiment and importance.
- **Search research documents** — a mini "ask questions about a document"
  system (RAG).
- **Score companies** — a 0–100 scorecard (growth / risk / sentiment).
- **Predict the next price move** — a simple, honest machine-learning baseline.
- **Fuse all signals** into one Buy / Hold / Sell recommendation.
- **Reason** — produce a bullish/bearish/neutral opinion *with a written
  explanation*.
- **Backtest** — "if I had invested ₹100,000 in AAPL two years ago, what would
  it be worth?" with proper risk metrics.

Everything is shown to the user in **Indian Rupees (INR)**.

It is built to run **fully offline** (no internet, no accounts, no API keys)
using a local file database, so you can explore it safely.

---

## 2. Run it in 5 minutes

You need **Python 3.11** installed. Check with `python --version`.
(Python 3.14 can fail to install some packages here — stick with 3.11.)

Open **PowerShell** in the project folder and run:

```powershell
# 1. Create an isolated Python environment (a private box for this project's tools)
py -3.11 -m venv .venv

# 2. Turn it on (you'll see "(.venv)" appear at the start of your prompt)
.venv\Scripts\Activate.ps1

# 3. Install the project's tools
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Go into the app folder and start the server
cd main
python main.py --reload
```

Now open your browser at **<http://127.0.0.1:8000/docs>**.

That page is **auto-generated**. Every box is an endpoint (an action the backend
can do). Click one → "Try it out" → "Execute", and you'll see the real
response. Start with `GET /health` (it just says "healthy").

> **No `.env` file needed.** With no configuration, the app uses a local file
> database (`prospera.db`) and works offline. Features that need the internet
> (live quotes, news) will simply say they need an API key — everything else
> works.

**To check everything is wired up correctly**, in a second PowerShell (with the
venv active, inside `main`):

```powershell
python test_api.py          # runs the app in-memory and exercises it end-to-end
```

You should see a list of `[PASS]` lines and `FAILED: 0`.

---

## 3. Every tool, explained plainly

You don't need to know these deeply. This is a "what is that word?" reference.

| Tool | What it is (plain English) | Where you meet it |
|------|-----------------------------|-------------------|
| **Python 3.11** | The programming language everything is written in. | `.py` files everywhere |
| **virtual environment (`venv`)** | A private box holding this project's tools so they don't clash with other projects. `.venv\Scripts\Activate.ps1` turns it on. | `.venv/` folder |
| **pip** | Python's app store. `pip install -r requirements.txt` downloads the tools listed in that file. | `requirements*.txt` |
| **FastAPI** | The web framework. It takes an incoming web request, finds the right Python function, checks the input, and turns your answer into JSON. It also builds the `/docs` page for free. | `backend/api/`, `backend/app.py` |
| **uvicorn** | The actual server program that listens on a network port (8000) for browsers/scripts and hands requests to FastAPI. | `python main.py` starts it |
| **Pydantic** | Checks that incoming/outgoing data has the right shape and types. Also loads settings from `.env`. | `backend/core/config.py`, request bodies |
| **SQLAlchemy** | Lets us work with database rows as Python objects instead of writing raw SQL by hand. The "async" version means the server can handle other requests while waiting on the database. | `backend/**/infrastructure/` |
| **SQLite** | A database that is just a single file (`prospera.db`). Zero setup. Great for learning. | default `DATABASE_URL` |
| **PostgreSQL** | A "real" database server for production. Same code works with it — you just change one setting. | optional |
| **Redis** | A fast in-memory cache. Listed for the future; **not used yet**. | future |
| **httpx** | How *our* server calls *other* servers (e.g. Finnhub) over the internet. We are both a server and a client. | market data / news / LLM |
| **Finnhub** | An outside company that provides live stock quotes and news (needs a free API key). | `MARKET_DATA_API_KEY` |
| **yfinance** | A free library that fetches historical prices and company info (no key, but unofficial). Also used for live currency rates. | market data, FX |
| **pytest** | The tool that runs our automated tests. `pytest backend/tests`. | `backend/tests/` |
| **ruff** | A "linter": it flags messy or broken code (unused imports, etc.) very fast. | `ruff check backend/` |
| **git / GitHub** | Version control: saves snapshots of the code and pushes them online so nothing is lost. | `git ...`, GitHub Actions |
| **GitHub Actions** | A robot that runs our tests automatically every time we push code. | `.github/workflows/ci.yml` |
| **Ollama** | A program that runs AI language models (like Llama) **locally** on your PC. Prospera talks to it — it never downloads models itself. | AI features (optional) |
| **Docker** | Packages an app so it runs identically anywhere. Listed for the future; **not used yet**. | future |

---

## 4. The mental model: how a request flows

You know a browser talks to a server over the internet. Here is what happens
inside Prospera when you click "Execute" on, say, "create environment":

```
You (browser / curl / script)
   │  HTTP request:  POST /api/v1/environments   { "name": "...", "owner_type": "user" }
   ▼
uvicorn        ← the server process, listening on port 8000
   ▼
FastAPI        ← matches the URL to a Python function ("route handler")
   ▼
Route          backend/api/routes/environments.py   ← thin: just receives + returns
   ▼
Service        backend/modules/simulator/application/services.py  ← the coordinator
   ▼
Use case       .../application/commands.py    ← ONE business action (the actual rule)
   ▼
Domain         .../domain/entities.py, value_objects.py  ← the core concepts + invariants
   ▼
Repository     .../infrastructure/repositories.py  ← reads/writes the database
   ▼
Database       prospera.db (SQLite) or PostgreSQL
```

The reply travels back up the same path and FastAPI turns it into JSON.

**The golden rule of this codebase:** each layer only talks to the one just
below it. Routes never touch the database; the database code never knows about
HTTP. This is called **Clean Architecture**, and it's why the project stays
tidy as it grows.

---

## 5. How the code is organized

Everything lives under `main/backend/`:

```
backend/
├── app.py                  # Builds the FastAPI application (start here conceptually)
├── api/                    # The HTTP layer (the "front door")
│   ├── router.py           #   lists every route group
│   ├── dependencies.py     #   wiring: builds each service and hands it its parts
│   └── routes/             #   one file per feature (environments, market_data, …)
├── core/                   # Cross-cutting basics
│   ├── config.py           #   all settings (reads .env, with safe defaults)
│   ├── database.py         #   the shared DB connection + "create all tables"
│   ├── logging.py          #   consistent, request-tagged logs
│   └── exceptions.py       #   the project's error types
├── shared/                 # Tiny building blocks used everywhere
│   ├── types.py            #   Money, Symbol, OwnerType, …
│   ├── fx.py               #   currency conversion rate table
│   └── llm.py              #   the tiny client that talks to a local LLM
├── modules/                # The business features (each is a self-contained "module")
│   ├── simulator/          #   paper-trading portfolios
│   ├── market_data/        #   quotes, history, company profiles, currency conversion
│   ├── news/               #   news warehouse
│   ├── events/             #   structured events from news
│   ├── research/           #   document search (RAG)
│   ├── company/            #   company scorecards
│   ├── prediction/         #   price-move forecasts
│   ├── signals/            #   Buy/Hold/Sell fusion
│   ├── reasoning/          #   explainable opinions
│   └── backtesting/        #   "what if I had invested…" simulations
└── tests/                  # Automated tests (one file per module)
```

**Every module has the same three layers** (this repetition is on purpose — once
you understand one module, you understand them all):

```
modules/<name>/
├── domain/            # The pure ideas: entities, rules, math. No database, no internet.
├── application/       # The coordinators: "services" that run a workflow step by step.
└── infrastructure/    # The messy real world: database tables, external APIs, adapters.
```

A quick way to remember it:
- **domain** = *what* things are and the rules they must obey.
- **application** = *how* a task gets done (the recipe).
- **infrastructure** = *where* data actually comes from / goes to.

---

## 6. A guided tour — read the code in this order

Reading a new codebase top-to-bottom is overwhelming. Follow this path instead.
Open each file, skim it, then move on. (Paths are clickable in VS Code.)

**Step 1 — See the whole surface.**
Start the server and open `/docs`. Every capability is listed there. This is
your map.

**Step 2 — The entry point.**
[`main/main.py`](main/main.py) → starts the server.
[`main/backend/app.py`](main/backend/app.py) → builds the app, adds logging,
error handling, and creates database tables on startup.

**Step 3 — One simple feature, end to end.** Follow "create an environment":
1. [`backend/api/routes/environments.py`](main/backend/api/routes/environments.py) — the route (very short).
2. [`backend/modules/simulator/application/services.py`](main/backend/modules/simulator/application/services.py) — the service it calls.
3. [`backend/modules/simulator/application/commands.py`](main/backend/modules/simulator/application/commands.py) — `CreateEnvironmentUseCase` (the actual logic).
4. [`backend/modules/simulator/domain/entities.py`](main/backend/modules/simulator/domain/entities.py) — what an "environment" *is*.
5. [`backend/modules/simulator/infrastructure/repositories.py`](main/backend/modules/simulator/infrastructure/repositories.py) — how it's saved.

**Step 4 — The wiring.**
[`backend/api/dependencies.py`](main/backend/api/dependencies.py) — this is the
"composition root". It's where every service is assembled from its parts and
where you'd swap a real implementation for a fake one. Read
`get_simulator_service` slowly; it names every piece.

**Step 5 — The shared building blocks.**
[`backend/shared/types.py`](main/backend/shared/types.py) — meet `Money` (note it
rounds and refuses to mix currencies) and the ID types.

**Step 6 — A "smart" module.**
Read the whole `company` module (it's small and self-contained):
`domain/scoring.py` (pure math you can read like a formula) →
`application/services.py` (gathers data, calls the math, stores the result) →
`infrastructure/` (the table + how it's saved). This is the template every
intelligence module follows.

By now you'll recognize the pattern everywhere.

---

## 7. The modules, one by one

Each module answers a question. Here's the map, roughly in dependency order.

| Module | Answers | Key endpoints |
|--------|---------|---------------|
| `market_data` | "What's the price / history / profile?" (in INR) | `GET /market-data/quote/{sym}`, `/history/{sym}`, `/profile/{sym}` |
| `simulator` | "Let me trade with virtual money." | `POST /environments`, `/portfolios/{id}/buy` |
| `news` | "Give me clean, classified news." | `POST /news/sync`, `GET /news/company/{sym}` |
| `events` | "Turn that news into structured facts." | `POST /events/extract`, `GET /events` |
| `research` | "Search my documents for an answer." | `POST /research/documents`, `/research/search` |
| `company` | "How healthy is this company?" (0–100) | `POST /company/analyze/{sym}` |
| `prediction` | "Will it go up or down next?" | `POST /predictions/predict/{sym}` |
| `signals` | "So… buy, hold, or sell?" | `POST /signals/fuse/{sym}` |
| `reasoning` | "Explain the call in words." | `POST /reasoning/analyze/{sym}` |
| `backtesting` | "What if I had invested back then?" | `POST /backtest/lumpsum`, `/backtest/sip` |

**How they connect (the intelligence pipeline):**

```
news ──► events ─┐
                 ├──► signals ──► reasoning
company ─────────┤        ▲
prediction ──────┘        │
research ─────────────────┘
```

`signals` blends the outputs of `events`, `company`, and `prediction` into one
decision; `reasoning` then writes the human explanation, optionally grounded in
`research`. To get a fully-informed reasoning result, run `analyze`/`predict`/
`fuse` for a symbol first — each stored result feeds the next stage.

---

## 8. How money and currency work (INR)

Prospera shows **every value to the user in Indian Rupees (INR)** — even for a
US stock like AAPL that natively trades in US Dollars.

- **Where conversion happens:** the market-data layer converts foreign prices to
  INR. Historical prices are converted **when they are fetched and stored**, so
  the database holds INR. Live quotes are converted **when served**.
- **The exchange rate:** by default a **real-time** rate is pulled from yfinance
  (e.g. the `USDINR=X` pair) and cached for an hour. If that lookup fails (or
  you set `FX_LIVE=false`), a fixed fallback rate from settings is used, so the
  app always works offline.
- **Your portfolio:** environments, cash, trades, holdings, and transactions are
  all denominated in INR.
- **Known simplification:** a whole historical price series is converted using a
  single rate (not each day's historical rate). This preserves *percentage*
  returns exactly and is fine for a learning/simulator project; per-day
  historical FX is a future enhancement.

The relevant code: [`backend/shared/fx.py`](main/backend/shared/fx.py) (the rate
table), [`backend/modules/market_data/infrastructure/fx.py`](main/backend/modules/market_data/infrastructure/fx.py)
(live + fallback providers), and the conversion calls inside
[`market_data/application/services.py`](main/backend/modules/market_data/application/services.py).

---

## 9. Using the AI features (your local Llama)

The "smart text" features (LLM event extraction, LLM reasoning) can use a
**large language model you already run locally** — Prospera **never downloads a
model** and adds **no new Python packages** for this. It simply makes a web call
to an OpenAI-compatible endpoint.

The easiest local option is **Ollama**:

1. Install Ollama and pull a model you already have, e.g. `ollama pull llama3.1`.
2. In your `.env`, set:
   ```
   LLM_ENABLED=true
   LLM_BASE_URL=http://localhost:11434/v1
   LLM_MODEL=llama3.1
   ```
3. Restart the server. Now `POST /events/extract` and `POST /reasoning/analyze`
   use the model.

If `LLM_ENABLED=false` (the default), the app uses **deterministic** versions
(rule-based extraction, template-based reasoning) that need no model at all — so
the tests and CI never touch the network. If the model is enabled but a call
fails, the code automatically falls back to the deterministic version. You never
get a broken feature.

The tiny client lives in [`backend/shared/llm.py`](main/backend/shared/llm.py).

---

## 10. How to add a new feature (recipe)

Say you want a new endpoint. Follow the module pattern:

1. **Domain** — in `modules/<name>/domain/`, define the *thing* (an entity /
   dataclass) and any pure rules or math. No database, no internet here.
2. **Application** — in `modules/<name>/application/`:
   - `dto.py`: the request/response shapes.
   - `services.py`: a service class with one method per action. It calls domain
     rules and repositories.
   - If you have a swappable strategy (a model, an extractor…), define a
     `Contract` (an abstract base class) here — a "port".
3. **Infrastructure** — in `modules/<name>/infrastructure/`:
   - `models.py`: the database table (SQLAlchemy) + a `.sql` migration.
   - `repositories.py`: an `InMemory…` version (for tests) **and** a `Sql…`
     version (for real use).
4. **API** — add `backend/api/routes/<name>.py` with the endpoints, register it
   in [`backend/api/router.py`](main/backend/api/router.py), and add a
   `get_<name>_service` builder in
   [`backend/api/dependencies.py`](main/backend/api/dependencies.py).
5. **Schema** — if you added a table, add your module's `Base` to
   `_module_metadata()` in [`backend/core/database.py`](main/backend/core/database.py)
   so it's auto-created.
6. **Tests** — add `backend/tests/test_<name>_pipeline.py`. Test the pure domain
   math directly, and the service using the `InMemory…` repositories (no
   database or network needed).

Copy the `company` or `prediction` module as your starting template — they are
small and follow this recipe exactly.

---

## 11. Testing, linting, and CI

All commands run from the `main/` folder with the venv active.

```powershell
# Run the whole test suite (fast, fully offline)
python -m pytest backend/tests -v

# Run one module's tests
python -m pytest backend/tests/test_backtesting_pipeline.py -v

# Lint (flags messy/broken code)
ruff check backend/

# End-to-end smoke test (boots the app in memory, exercises the API)
python test_api.py                 # tries live features too, skips them if no key
python test_api.py --skip-network  # offline only
```

Why the tests are trustworthy:
- They use the `InMemory…` repositories and stub data, so **no database and no
  internet are required** — they run the same on your laptop and on GitHub.
- The AI and market-data code is exercised through **fakes/stubs**, so results
  are deterministic.

**CI (GitHub Actions):** every push runs ruff + the tests + the offline smoke
test automatically (see [`.github/workflows/ci.yml`](.github/workflows/ci.yml)).
If the badge/checkmark on GitHub is green, the code is healthy.

---

## 12. Everyday git workflow

git saves snapshots ("commits") and pushes them to GitHub so your work is safe.

```powershell
git status                     # what changed?
git add -A                     # stage all changes
git commit -m "Describe what you did"
git push origin main           # send it to GitHub
```

Good habits used in this project:
- Commit after each meaningful chunk (a phase, a fix), not once at the very end.
- Write a message that says *what* and *why*, not just "update".
- Never commit secrets. Real keys live in `.env`, which is **git-ignored**.
  `progress.md`, `notes.txt`, and `PLAN.md` are also git-ignored personal files.

---

## 13. Troubleshooting

| Symptom | Fix |
|--------|-----|
| `ModuleNotFoundError: No module named 'backend'` | Run commands from the `main/` folder (e.g. `cd main` first). |
| Port 8000 already in use | `python main.py --port 8001` |
| Market-data / news endpoints error about an API key | They need a free Finnhub key in `.env` (`MARKET_DATA_API_KEY=...`). Everything else works without it. |
| Backtest says "not enough price history" | The historical sync only appends *forward* from the newest stored date. Use a fresh DB (delete `prospera.db`) or a window newer than what's already stored. |
| Dependencies won't install | Make sure you're on **Python 3.11** (`python --version`) and the venv is active. |
| Weird database errors after schema changes | For local SQLite, stop the server and delete `prospera.db`; it will be recreated on next start. |

---

## 14. Glossary (finance + tech words)

**Backend** — the server-side program; it stores data and does the work. No
buttons of its own; other programs talk to it.

**API / endpoint** — a specific action the backend offers at a URL (e.g.
`POST /environments`). The set of them is the API.

**REST / JSON** — a common style of API; JSON is the simple text format
(`{ "key": "value" }`) used to send data back and forth.

**Route handler** — the Python function that runs for one endpoint.

**Service / use case** — the code that performs a business action (create a
portfolio, score a company).

**Repository** — the code that reads/writes the database for one kind of thing.

**Entity / value object** — a plain Python object representing a business
concept (an Environment, a Money amount). Value objects (like `Money`) are
immutable and enforce their own rules.

**Migration** — a `.sql` file describing a database table, applied to set up the
schema.

**RAG (Retrieval-Augmented Generation)** — answering a question by first
*retrieving* relevant text (from your documents) so answers are grounded in real
sources instead of guessed.

**LLM (Large Language Model)** — an AI model that reads and writes text (e.g.
Llama). We call one running locally via Ollama.

**Paper trading** — practicing trades with fake money at real prices.

**Portfolio / holdings** — the set of stocks you own and how much.

**P&L (Profit and Loss)** — how much money you've made or lost. *Unrealized* =
on stocks you still hold; *realized* = locked in after selling.

**Quote** — the current price of a stock.

**OHLCV** — Open, High, Low, Close, Volume: the standard daily price summary.

**Bullish / Bearish / Neutral** — expecting the price to rise / fall / stay flat.

**Buy / Hold / Sell** — the action recommendation derived from the signals.

**Sentiment** — whether news about a company is positive, negative, or neutral.

**Backtest** — replaying history to see how a strategy *would* have performed.

**Lump sum** — investing one amount once.

**SIP (Systematic Investment Plan)** — investing a fixed amount every month.

**CAGR (Compound Annual Growth Rate)** — the smoothed yearly growth rate.

**XIRR** — an annual return that correctly accounts for money added at different
times (the right measure for SIPs).

**Volatility** — how much the price bounces around; a proxy for risk.

**Sharpe / Sortino ratio** — return earned per unit of risk (higher is better);
Sortino only counts *downside* risk.

**Max drawdown** — the worst peak-to-trough drop; "how bad did it get?".

**INR** — Indian Rupees, the currency everything is shown in.

**FX** — foreign exchange; converting one currency to another.

---

*New to the project? Do the [5-minute run](#2-run-it-in-5-minutes), open
`/docs`, then follow the [guided tour](#6-a-guided-tour--read-the-code-in-this-order).
Questions about a word? It's probably in the [glossary](#14-glossary-finance--tech-words).*
