CREATE TABLE IF NOT EXISTS fused_signals (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(32) NOT NULL,
    as_of TIMESTAMPTZ NOT NULL,
    action VARCHAR(8) NOT NULL,
    score DOUBLE PRECISION NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    components JSONB NOT NULL DEFAULT '[]'::jsonb,
    rationale JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_fused_signals_symbol ON fused_signals (symbol);
CREATE INDEX IF NOT EXISTS ix_fused_signals_as_of ON fused_signals (as_of);
CREATE INDEX IF NOT EXISTS ix_fused_signals_symbol_as_of ON fused_signals (symbol, as_of);

-- Phase 13 signal fusion.
--
-- One row per fusion run: a unified Buy/Hold/Sell decision blended from the
-- news (Phase 8), company (Phase 10), and prediction (Phase 12) signals, with
-- the full component breakdown and rationale retained for explainability.
