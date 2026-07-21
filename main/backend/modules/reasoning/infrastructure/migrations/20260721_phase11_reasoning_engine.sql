CREATE TABLE IF NOT EXISTS reasoned_opinions (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(32) NOT NULL,
    as_of TIMESTAMPTZ NOT NULL,
    stance VARCHAR(16) NOT NULL,
    headline VARCHAR(512) NOT NULL,
    explanation TEXT NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    drivers JSONB NOT NULL DEFAULT '[]'::jsonb,
    citations JSONB NOT NULL DEFAULT '[]'::jsonb,
    source VARCHAR(32) NOT NULL DEFAULT 'deterministic',
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_reasoned_opinions_symbol ON reasoned_opinions (symbol);
CREATE INDEX IF NOT EXISTS ix_reasoned_opinions_as_of ON reasoned_opinions (as_of);
CREATE INDEX IF NOT EXISTS ix_reasoned_opinions_symbol_as_of
    ON reasoned_opinions (symbol, as_of);

-- Phase 11 explainable reasoning.
--
-- One row per reasoning run: a bullish/bearish/neutral stance plus a written
-- explanation, the drivers behind it, and research citations. The default
-- reasoner is deterministic/template-based; an LLM reasoner produces a richer
-- narrative behind the same ReasonerContract.
