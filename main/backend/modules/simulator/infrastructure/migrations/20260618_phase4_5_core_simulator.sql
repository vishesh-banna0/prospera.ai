CREATE TABLE IF NOT EXISTS environments (
    environment_id VARCHAR(36) PRIMARY KEY,
    owner_type VARCHAR(20) NOT NULL,
    name VARCHAR(255) NOT NULL,
    cash_balance NUMERIC(18, 2) NOT NULL,
    currency VARCHAR(8) NOT NULL DEFAULT 'USD',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_environments_owner_type
    ON environments (owner_type);

CREATE TABLE IF NOT EXISTS holdings (
    holding_id VARCHAR(36) PRIMARY KEY,
    environment_id VARCHAR(36) NOT NULL REFERENCES environments(environment_id) ON DELETE CASCADE,
    symbol VARCHAR(32) NOT NULL,
    quantity NUMERIC(20, 8) NOT NULL,
    average_cost NUMERIC(18, 2) NOT NULL,
    currency VARCHAR(8) NOT NULL DEFAULT 'USD',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_holdings_symbol
    ON holdings (symbol);

CREATE INDEX IF NOT EXISTS ix_holdings_environment_id
    ON holdings (environment_id);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id VARCHAR(36) PRIMARY KEY,
    environment_id VARCHAR(36) NOT NULL REFERENCES environments(environment_id) ON DELETE CASCADE,
    transaction_type VARCHAR(20) NOT NULL,
    symbol VARCHAR(32),
    quantity NUMERIC(20, 8),
    executed_price NUMERIC(18, 2),
    amount NUMERIC(18, 2) NOT NULL,
    currency VARCHAR(8) NOT NULL DEFAULT 'USD',
    notes VARCHAR(500),
    executed_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_transactions_environment_id_executed_at
    ON transactions (environment_id, executed_at);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id BIGSERIAL PRIMARY KEY,
    environment_id VARCHAR(36) NOT NULL REFERENCES environments(environment_id) ON DELETE CASCADE,
    snapshot_at TIMESTAMPTZ NOT NULL,
    cash_balance NUMERIC(18, 2) NOT NULL,
    portfolio_value NUMERIC(18, 2) NOT NULL,
    total_value NUMERIC(18, 2) NOT NULL,
    unrealized_pnl NUMERIC(18, 2) NOT NULL,
    currency VARCHAR(8) NOT NULL DEFAULT 'USD'
);

CREATE INDEX IF NOT EXISTS ix_portfolio_snapshots_environment_id_snapshot_at
    ON portfolio_snapshots (environment_id, snapshot_at);
