# Prospera

> Transforming information into intelligent decisions that create long-term prosperity.

## Overview

Prospera is an agentic financial intelligence platform designed to turn market data, news, research, and predictive models into explainable investment intelligence.

The platform starts with a strong backend foundation: a multi-environment market simulator powered by a centralized market data service. Over time, that foundation expands into research, reasoning, prediction, backtesting, and autonomous portfolio management.

## Current Scope

The current focus is **V1 backend foundation**.

V1 includes:
- A market simulator engine
- Isolated portfolio environments
- A centralized market data service
- Clean backend architecture for future expansion

V1 does not yet include:
- News intelligence pipelines
- Research RAG implementation
- Prediction model training
- RL agents
- Full frontend implementation

## Product Vision

Prospera is being designed to support:
- Market simulation
- Portfolio management
- Market data intelligence
- News intelligence
- Financial research RAG
- Company analysis
- Prediction models
- Backtesting
- F&O intelligence
- Multi-agent reasoning
- Reinforcement learning

The long-term goal is not just prediction. The goal is to build a transparent and explainable financial intelligence system that helps users and AI agents make higher-quality investment decisions.

## Architecture Principles

The backend is being built around a few strict principles:
- Clean Architecture
- Separation of concerns
- Service layer pattern
- Isolated business modules
- Shared market data access through one internal service
- Minimal V1 scope with room for future scale

## System Overview

The core system is centered on two foundation components:
- `Market Data Service`: the single internal gateway for quotes, history, symbol lookup, and metadata
- `Market Simulator`: the isolated environment engine used by users, AI agents, and future RL agents

```mermaid
flowchart TD
    FE[Frontend / Future UI]
    API[FastAPI API Layer]
    MDS[Market Data Service]
    SIM[Market Simulator Engine]
    ENV1[User Environment]
    ENV2[AI Environment]
    ENV3[RL / Backtesting Environment]
    EXT[External Market APIs]
    DB[(PostgreSQL)]
    CACHE[(Redis - Future)]

    FE --> API
    API --> SIM
    API --> MDS
    EXT --> MDS
    MDS --> CACHE
    MDS --> SIM
    SIM --> ENV1
    SIM --> ENV2
    SIM --> ENV3
    SIM --> DB
```

## V1 Simulator Flow

Each simulator environment is independent. All environments use the same market data service, but each one maintains its own cash, holdings, transactions, and performance history.

```mermaid
flowchart LR
    A[Create Environment] --> B[Add Virtual Cash]
    B --> C[Buy / Sell Stocks]
    C --> D[Update Holdings]
    C --> E[Record Transactions]
    D --> F[Calculate Portfolio Performance]
    E --> F
    M[Market Data Service] --> C
    M --> F
```

## Intelligence Evolution Flow

The V1 simulator is the foundation. Future intelligence layers will be built on top of the same shared data and portfolio infrastructure.

```mermaid
flowchart TD
    MDS[Market Data Service]
    NEWS[News Intelligence]
    RAG[Financial Research RAG]
    CA[Company Analysis]
    PM[Prediction Models]
    SF[Signal Fusion]
    RE[Reasoning Engine]
    APM[AI Portfolio Manager]
    BT[Backtesting Engine]
    RL[RL Portfolio Agent]

    MDS --> NEWS
    MDS --> CA
    MDS --> PM
    NEWS --> SF
    RAG --> SF
    CA --> SF
    PM --> SF
    SF --> RE
    RE --> APM
    APM --> BT
    APM --> RL
```

## Daily Intelligence Pipeline

At maturity, Prospera is expected to operate as a continuous intelligence pipeline.

```mermaid
flowchart TD
    A[Market Data]
    B[Financial News]
    C[Company Information]
    D[Financial Research]
    E[Data Processing]
    F[Signal Generation]
    G[Reasoning Engine]
    H[Investment Recommendations]
    I[Portfolio Decisions]
    J[Performance Evaluation]
    K[Continuous Learning]

    A --> E
    B --> E
    C --> E
    D --> E
    E --> F
    F --> G
    G --> H
    H --> I
    I --> J
    J --> K
```

## Backend Folder Structure

The backend is organized by responsibility, not by framework convenience.

```text
main/
└── backend/                     # Backend root and application assembly boundary
    ├── api/                     # HTTP transport layer and route composition
    │   └── routes/              # Endpoint groups for environments, portfolios, and market data
    ├── core/                    # Cross-cutting configuration and shared backend concerns
    ├── modules/                 # Business modules grouped as bounded contexts
    │   ├── simulator/           # Isolated market simulator domain
    │   │   ├── domain/          # Business entities, value objects, policies, repository contracts
    │   │   ├── application/     # Commands, queries, DTOs, and service orchestration
    │   │   └── infrastructure/  # Persistence models and repository implementations
    │   └── market_data/         # Shared market data service boundary
    │       ├── domain/          # Quotes, instruments, history, and provider-agnostic contracts
    │       ├── application/     # Internal market data use cases and service contracts
    │       └── infrastructure/  # Provider clients, adapters, and caching implementations
    ├── shared/                  # Small shared primitives used across modules
    ├── app.py                   # Future FastAPI entry point
    └── __init__.py              # Backend package marker
```

## Folder Responsibility Guide

### `backend/api`

Purpose:
Expose backend capabilities through HTTP interfaces.

Should contain:
Routers, request mapping, response mapping, and dependency wiring.

Should not contain:
Trading logic, database queries, or direct external market API calls.

### `backend/core`

Purpose:
Hold shared operational concerns used across the backend.

Should contain:
Configuration, shared exceptions, and future app lifecycle helpers.

Should not contain:
Business workflows or module-specific logic.

### `backend/modules/simulator`

Purpose:
Own the V1 market simulator and environment-isolation model.

Should contain:
Environment lifecycle, cash operations, trades, holdings, transactions, and performance workflows.

Should not contain:
Direct vendor integrations or unrelated intelligence modules.

### `backend/modules/market_data`

Purpose:
Provide a centralized internal gateway for market information.

Should contain:
Quote retrieval, historical prices, symbol lookup, metadata, provider abstractions, and future cache integration.

Should not contain:
Portfolio rules or simulator state management.

### `backend/shared`

Purpose:
Provide small reusable primitives shared across modules.

Should contain:
Identifiers, timestamps, enums, and generic shared types.

Should not contain:
Large generic utility collections or feature-specific code.

## Tech Stack

### Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- PostgreSQL
- Redis

### Frontend

- Next.js
- React
- Tailwind CSS

### AI and ML

- LangGraph
- Local LLMs
- XGBoost
- LightGBM
- PyTorch
- Reinforcement Learning

### Infrastructure

- Docker
- GitHub
- GitHub Actions

## Backend Environment Setup

The backend should currently be set up with **Python 3.11**.

Python `3.14` may fail while installing dependencies in this stack because some packages, especially `pydantic-core`, may not resolve cleanly there in this environment.

Recommended setup:

```powershell
cd "c:\Users\vishe\OneDrive\Desktop\VS Code Workspaces\prospera.ai"
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

If a previous `.venv` was created with Python `3.14`, recreate it with Python `3.11`.

## Roadmap

### Phase 1
- System design
- Backend architecture
- Environment setup
- Database planning

### Phase 2
- Market simulator engine
- Portfolio operations
- Market data service

### Phase 3
- News collection and event extraction
- Research ingestion and RAG foundation

### Phase 4
- Company analysis
- Prediction models
- Signal fusion and reasoning

### Phase 5
- AI portfolio manager
- Backtesting engine
- RL environment integration

## Mission

Prospera exists to help people navigate uncertainty, transform information into insight, and make intelligent decisions that contribute to long-term prosperity.
