CREATE TABLE IF NOT EXISTS news_events (
    event_id VARCHAR(64) PRIMARY KEY,
    article_id VARCHAR(64) NOT NULL,
    event_type VARCHAR(32) NOT NULL,
    sentiment VARCHAR(16) NOT NULL,
    importance VARCHAR(16) NOT NULL,
    headline VARCHAR(512) NOT NULL,
    summary TEXT,
    symbols JSONB NOT NULL DEFAULT '[]'::jsonb,
    sectors JSONB NOT NULL DEFAULT '[]'::jsonb,
    keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    source VARCHAR(64) NOT NULL DEFAULT 'rule-based',
    event_date TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_news_events_event_type
    ON news_events (event_type);

CREATE INDEX IF NOT EXISTS ix_news_events_article_id
    ON news_events (article_id);

CREATE INDEX IF NOT EXISTS ix_news_events_event_date
    ON news_events (event_date);

CREATE INDEX IF NOT EXISTS ix_news_events_type_event_date
    ON news_events (event_type, event_date);

CREATE INDEX IF NOT EXISTS ix_news_events_sentiment
    ON news_events (sentiment);

CREATE INDEX IF NOT EXISTS ix_news_events_importance
    ON news_events (importance);

CREATE INDEX IF NOT EXISTS ix_news_events_symbols
    ON news_events USING GIN (symbols);

CREATE INDEX IF NOT EXISTS ix_news_events_sectors
    ON news_events USING GIN (sectors);

-- Phase 8 event extraction warehouse.
--
-- Stores structured events derived from news_articles (Phase 7). event_id is
-- a deterministic hash of (article_id, event_type, primary_symbol), so
-- re-running extraction over the same articles is idempotent (upsert by PK).
-- The article_id column is intentionally NOT a foreign key so events can be
-- retained/analyzed independently of article-warehouse retention policies.
