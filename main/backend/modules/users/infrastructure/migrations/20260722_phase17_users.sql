-- Phase 17: user accounts for simple username/password authentication.
-- Passwords are stored only as a PBKDF2-SHA256 hash (see infrastructure/security.py),
-- never in plain text.

CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_users_username
    ON users (username);
