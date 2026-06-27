CREATE TABLE IF NOT EXISTS market_instruments (
    symbol VARCHAR(32) PRIMARY KEY,
    instrument_name VARCHAR(255) NOT NULL,
    exchange VARCHAR(64) NOT NULL,
    native_currency VARCHAR(8) NOT NULL,
    asset_type VARCHAR(32) NOT NULL DEFAULT 'stock',
    isin VARCHAR(32),
    sector VARCHAR(128),
    industry VARCHAR(128),
    country VARCHAR(64),
    provider_symbol VARCHAR(64),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_market_instruments_sector
    ON market_instruments (sector);

CREATE INDEX IF NOT EXISTS ix_market_instruments_industry
    ON market_instruments (industry);

CREATE TABLE IF NOT EXISTS historical_price_bars (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(32) NOT NULL REFERENCES market_instruments(symbol),
    price_date DATE NOT NULL,
    open_price NUMERIC(20, 6) NOT NULL,
    high_price NUMERIC(20, 6) NOT NULL,
    low_price NUMERIC(20, 6) NOT NULL,
    close_price NUMERIC(20, 6) NOT NULL,
    adjusted_close_price NUMERIC(20, 6),
    volume BIGINT NOT NULL,
    split_coefficient NUMERIC(20, 8),
    dividend_amount NUMERIC(20, 6),
    source VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ,
    CONSTRAINT uq_historical_price_bars_symbol_price_date
        UNIQUE (symbol, price_date)
);

CREATE INDEX IF NOT EXISTS ix_historical_price_bars_symbol_price_date
    ON historical_price_bars (symbol, price_date);

CREATE TABLE IF NOT EXISTS company_profiles (
    symbol VARCHAR(32) PRIMARY KEY REFERENCES market_instruments(symbol),
    instrument_name VARCHAR(255) NOT NULL,
    native_currency VARCHAR(8) NOT NULL,
    exchange VARCHAR(64) NOT NULL,
    asset_type VARCHAR(32) NOT NULL,
    sector VARCHAR(128),
    industry VARCHAR(128),
    country VARCHAR(64),
    website VARCHAR(255),
    description TEXT,
    market_cap NUMERIC(24, 2),
    employees BIGINT,
    source VARCHAR(64),
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_company_profiles_sector
    ON company_profiles (sector);

CREATE INDEX IF NOT EXISTS ix_company_profiles_industry
    ON company_profiles (industry);
