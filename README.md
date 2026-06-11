# Prospera

> Transforming information into intelligent decisions that create long-term prosperity.

## Overview

Prospera is an Agentic Financial Intelligence Platform designed to help users make better investment decisions through a combination of market data, financial research, news analysis, prediction models, portfolio simulation, and AI-driven reasoning.

Unlike traditional stock prediction systems, Prospera focuses on building a complete financial intelligence ecosystem that combines structured financial data, unstructured research documents, market sentiment, forecasting models, and explainable decision-making.

The platform begins as a market simulator and gradually evolves into a multi-agent financial intelligence system capable of portfolio analysis, market reasoning, backtesting, and reinforcement learning-based portfolio optimization.

---

## Vision

The goal of Prospera is not simply to predict market movements.

The goal is to build an intelligent system capable of:

* Understanding financial information
* Analyzing market conditions
* Evaluating investment opportunities
* Explaining decisions
* Simulating investment strategies
* Learning from historical outcomes

---

## Core Features

### Market Simulator

* Virtual trading environment
* Portfolio management
* Transaction tracking
* Profit and loss analysis
* Watchlists

### Financial Intelligence Engine

* Market data analysis
* Company research
* Financial statement analysis
* Investment signal generation
* Explainable recommendations

### News Intelligence

* Financial news aggregation
* Event extraction
* Sentiment analysis
* Market impact detection
* Company-specific signal generation

### Financial Research RAG

* Annual reports
* Earnings call transcripts
* Investor presentations
* Research reports
* Semantic search over financial documents

### Prediction Models

* Traditional machine learning models
* Time-series forecasting
* Market trend prediction
* Signal generation

### F&O Intelligence

* Option chain analysis
* Open Interest analysis
* Put Call Ratio analysis
* Derivatives sentiment indicators

### Multi-Agent Architecture

* News Agent
* Research Agent
* Market Agent
* Company Agent
* Prediction Agent
* F&O Agent
* Reasoning Agent

### Reinforcement Learning

* Portfolio optimization
* Dynamic allocation strategies
* Risk-adjusted decision making
* Learning through market simulation

---

## Project Philosophy

Prospera follows a signal-first architecture.

Instead of relying on a single prediction model, the platform combines multiple sources of intelligence:

```text
Market Data
+
Financial Research
+
News Signals
+
F&O Signals
+
Prediction Models
+
Reasoning Engine

↓

Investment Intelligence
```

The objective is to generate explainable and evidence-based decisions rather than black-box predictions.

---

## System Roadmap

### Phase 1

* System Design
* Infrastructure Setup
* Database Architecture

### Phase 2

* Market Simulator
* Portfolio Management
* Market Data Pipeline

### Phase 3

* News Aggregation
* Event Extraction
* Sentiment Analysis

### Phase 4

* Financial Research RAG
* Company Intelligence Engine

### Phase 5

* Financial Reasoning Agent
* Explainable Decision Engine

### Phase 6

* Prediction Models
* Signal Fusion Layer

### Phase 7

* AI Portfolio Management
* Historical Backtesting

### Phase 8

* F&O Intelligence
* Multi-Agent System

### Phase 9

* Reinforcement Learning Portfolio Manager

### Phase 10

* Production Deployment
* Monitoring
* Scaling

---

## Long-Term Goals

* Build a fully explainable financial intelligence platform.
* Create an AI-driven investment research assistant.
* Support both retail and advanced investors.
* Enable historical strategy testing.
* Develop intelligent portfolio optimization systems.
* Create a scalable multi-agent financial ecosystem.

---

## Tech Stack (Planned)

### Frontend

* React
* Next.js
* Tailwind CSS

### Backend

* FastAPI
* Python

### Databases

* PostgreSQL
* Vector Database

### AI & ML

* Local LLMs
* LangGraph
* XGBoost
* LightGBM
* LSTM
* Reinforcement Learning

### Infrastructure

* Docker
* GitHub
* CI/CD

---

## Backend Folder Structure

The V1 backend is organized around two core backend capabilities:

* `simulator` for isolated market simulation environments
* `market_data` for shared stock and price data access

```text
main/
└── backend/                           # Backend application root; contains only backend-specific architecture and composition.
    ├── api/                           # HTTP/API transport layer; receives requests and delegates work to application services.
    │   └── routes/                    # Endpoint groups; separate route concerns by feature area such as environments, portfolios, and market data.
    ├── core/                          # Cross-cutting backend setup; place config, shared exceptions, and app-wide operational concerns here.
    ├── modules/                       # Business module boundary; each subfolder should represent a clean bounded context.
    │   ├── simulator/                 # Market simulator domain; owns isolated environments, cash, trades, holdings, and performance logic.
    │   │   ├── domain/                # Pure business rules and domain concepts; define entities, value objects, policies, and repository contracts here.
    │   │   ├── application/           # Use-case orchestration layer; coordinate commands, queries, and service-level workflows here.
    │   │   └── infrastructure/        # Persistence implementations and external technical details for the simulator module belong here.
    │   └── market_data/               # Shared market data service; this is the only module that should talk to external market data providers.
    │       ├── domain/                # Provider-agnostic market concepts; store quote, instrument, and history abstractions here.
    │       ├── application/           # Internal market data service contracts and use cases; expose quotes, history, search, and metadata here.
    │       └── infrastructure/        # Vendor clients, adapters, and cache implementations for market data should live here.
    ├── shared/                        # Small shared primitives reused across modules; keep this minimal and generic.
    ├── app.py                         # Future backend entry point; should create and wire the FastAPI application.
    └── __init__.py                    # Package marker for the backend root.
```

### Folder Responsibility Notes

#### `backend/`

Purpose:
Backend root for application assembly.

What should go here:
Application bootstrap files and top-level package organization.

What should not go here:
Business rules, database queries, or vendor-specific integrations.

#### `backend/api/`

Purpose:
Transport layer that exposes backend functionality to frontend clients, users, and future agents.

What should go here:
Routers, request/response mapping, dependency wiring, and HTTP-facing concerns.

What should not go here:
Trading logic, valuation rules, persistence implementation, or direct stock API calls.

#### `backend/api/routes/`

Purpose:
Feature-based route grouping.

What should go here:
Separate endpoint files for environment lifecycle, portfolio actions, and market data reads.

What should not go here:
Shared business workflows or repository logic.

#### `backend/core/`

Purpose:
Shared backend-wide operational building blocks.

What should go here:
Configuration, shared exceptions, and future middleware or lifecycle helpers.

What should not go here:
Module-specific entities, trading use cases, or provider clients.

#### `backend/modules/`

Purpose:
Home for backend business capabilities designed as bounded contexts.

What should go here:
Independent modules such as simulator, market data, and future domains like news or research.

What should not go here:
Generic utility dumping grounds or application bootstrap code.

#### `backend/modules/simulator/`

Purpose:
Owns the paper-trading and environment-isolation system for V1.

What should go here:
Environment lifecycle behavior, cash operations, trade workflows, holdings tracking, and performance-related business structure.

What should not go here:
Direct market vendor integrations or unrelated future modules.

#### `backend/modules/simulator/domain/`

Purpose:
Pure simulator business language and rules.

What should go here:
Entities like environment, holding, and transaction; value objects like money or symbol; policies; repository contracts.

What should not go here:
HTTP schemas, SQLAlchemy models, or route handlers.

#### `backend/modules/simulator/application/`

Purpose:
Use-case layer for simulator workflows.

What should go here:
Command handlers, query handlers, DTO definitions, and simulator service orchestration.

What should not go here:
Raw SQL, ORM table definitions, or vendor API client logic.

#### `backend/modules/simulator/infrastructure/`

Purpose:
Technical implementations required by the simulator module.

What should go here:
Persistence models, repository implementations, and future storage adapters.

What should not go here:
Core trading policies or route definitions.

#### `backend/modules/market_data/`

Purpose:
Centralized market data boundary shared by all simulator environments and future AI/RL consumers.

What should go here:
Everything related to quotes, historical prices, symbol lookup, metadata, provider abstraction, and cache strategy.

What should not go here:
Portfolio rules, environment state changes, or simulator-specific business workflows.

#### `backend/modules/market_data/domain/`

Purpose:
Common market data concepts independent of any specific provider.

What should go here:
Instrument entities, quote abstractions, historical price concepts, and repository contracts.

What should not go here:
Vendor response parsing, HTTP client code, or cache wiring.

#### `backend/modules/market_data/application/`

Purpose:
Internal service layer for market data access.

What should go here:
Use cases and service contracts for quote retrieval, historical data access, symbol search, and metadata retrieval.

What should not go here:
Concrete vendor implementations or simulator trade orchestration.

#### `backend/modules/market_data/infrastructure/`

Purpose:
Concrete integration layer for external market data systems.

What should go here:
Provider clients, adapters, retry strategy hooks, and cache implementations.

What should not go here:
Simulator entities, route handlers, or business policies.

#### `backend/shared/`

Purpose:
Small shared building blocks used across multiple modules.

What should go here:
Common IDs, timestamps, enums, and generic type definitions.

What should not go here:
Large helper collections, feature-specific logic, or cross-module shortcuts that weaken boundaries.

---

## Backend Environment Notes

The backend should currently be set up with Python `3.12`.

Python `3.14` may fail while installing backend dependencies because some packages in the FastAPI
and Pydantic stack do not consistently resolve prebuilt wheels for that interpreter yet in this setup.

Recommended commands:

```powershell
cd "c:\Users\vishe\OneDrive\Desktop\VS Code Workspaces\prospera.ai"
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

If you already created `.venv` with Python `3.14`, recreate the environment using Python `3.12`.

---

## Mission Statement

Prospera exists to help people navigate uncertainty, transform information into insight, and make intelligent decisions that contribute to long-term prosperity.
