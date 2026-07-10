CREATE TABLE IF NOT EXISTS news_articles (
    article_id VARCHAR(64) PRIMARY KEY,
    external_id VARCHAR(128),
    title VARCHAR(512) NOT NULL,
    summary TEXT,
    body TEXT,
    url VARCHAR(2048) NOT NULL,
    image_url VARCHAR(2048),
    source VARCHAR(255) NOT NULL,
    source_domain VARCHAR(255),
    category VARCHAR(32) NOT NULL,
    symbols JSONB NOT NULL DEFAULT '[]'::jsonb,
    sectors JSONB NOT NULL DEFAULT '[]'::jsonb,
    countries JSONB NOT NULL DEFAULT '[]'::jsonb,
    keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
    content_hash VARCHAR(64),
    published_at TIMESTAMPTZ NOT NULL,
    collected_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_news_articles_url UNIQUE (url)
);

CREATE INDEX IF NOT EXISTS ix_news_articles_external_id
    ON news_articles (external_id);

CREATE INDEX IF NOT EXISTS ix_news_articles_category
    ON news_articles (category);

CREATE INDEX IF NOT EXISTS ix_news_articles_published_at
    ON news_articles (published_at);

CREATE INDEX IF NOT EXISTS ix_news_articles_category_published_at
    ON news_articles (category, published_at);

CREATE INDEX IF NOT EXISTS ix_news_articles_content_hash
    ON news_articles (content_hash);

CREATE INDEX IF NOT EXISTS ix_news_articles_symbols
    ON news_articles USING GIN (symbols);

CREATE INDEX IF NOT EXISTS ix_news_articles_sectors
    ON news_articles USING GIN (sectors);

CREATE INDEX IF NOT EXISTS ix_news_articles_countries
    ON news_articles USING GIN (countries);
