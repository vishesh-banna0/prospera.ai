CREATE TABLE IF NOT EXISTS company_scores (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(32) NOT NULL,
    as_of TIMESTAMPTZ NOT NULL,
    overall_score DOUBLE PRECISION NOT NULL,
    growth_score DOUBLE PRECISION NOT NULL,
    risk_score DOUBLE PRECISION NOT NULL,
    sentiment_score DOUBLE PRECISION NOT NULL,
    rating VARCHAR(16) NOT NULL,
    company_name VARCHAR(256),
    sector VARCHAR(128),
    market_cap VARCHAR(64),
    event_count INTEGER NOT NULL DEFAULT 0,
    price_points INTEGER NOT NULL DEFAULT 0,
    rationale JSONB NOT NULL DEFAULT '[]'::jsonb,
    source VARCHAR(32) NOT NULL DEFAULT 'heuristic-v1',
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_company_scores_symbol
    ON company_scores (symbol);

CREATE INDEX IF NOT EXISTS ix_company_scores_as_of
    ON company_scores (as_of);

CREATE INDEX IF NOT EXISTS ix_company_scores_symbol_as_of
    ON company_scores (symbol, as_of);

-- Phase 10 company intelligence scorecards.
--
-- One row per (symbol, as_of) scoring run; history is retained so scores can be
-- tracked over time. Scores are transparent 0..100 heuristics derived from
-- price history (growth/risk) and news events (sentiment). True fundamental
-- ratios are a future enhancement once company profiles carry financials.
