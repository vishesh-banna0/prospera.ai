-- Phase 16: recurring (SIP) investment plans.
-- A plan is a forward-looking, scheduled contribution into one instrument.
-- Installments are executed lazily on a portfolio read once their run date
-- arrives; the executed buys land in the `transactions` table like any trade.

CREATE TABLE IF NOT EXISTS sip_plans (
    plan_id VARCHAR(36) PRIMARY KEY,
    environment_id VARCHAR(36) NOT NULL REFERENCES environments(environment_id) ON DELETE CASCADE,
    symbol VARCHAR(32) NOT NULL,
    symbol_name VARCHAR(255),
    amount NUMERIC(18, 2) NOT NULL,
    currency VARCHAR(8) NOT NULL DEFAULT 'INR',
    frequency VARCHAR(16) NOT NULL DEFAULT 'monthly',
    day_of_month INTEGER NOT NULL DEFAULT 1,
    start_date DATE NOT NULL,
    end_date DATE,
    next_run_date DATE NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    installments_run INTEGER NOT NULL DEFAULT 0,
    installments_skipped INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ,
    last_run_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_sip_plans_environment_id
    ON sip_plans (environment_id);

CREATE INDEX IF NOT EXISTS ix_sip_plans_next_run_date
    ON sip_plans (next_run_date);
