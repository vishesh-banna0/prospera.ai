CREATE TABLE IF NOT EXISTS predictions (
    prediction_id VARCHAR(64) PRIMARY KEY,
    symbol VARCHAR(32) NOT NULL,
    as_of TIMESTAMPTZ NOT NULL,
    horizon_days INTEGER NOT NULL,
    direction VARCHAR(16) NOT NULL,
    probability_up DOUBLE PRECISION NOT NULL,
    expected_return_pct DOUBLE PRECISION NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    model_name VARCHAR(64) NOT NULL,
    features JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_predictions_symbol ON predictions (symbol);
CREATE INDEX IF NOT EXISTS ix_predictions_as_of ON predictions (as_of);
CREATE INDEX IF NOT EXISTS ix_predictions_symbol_as_of ON predictions (symbol, as_of);

-- Phase 12 prediction forecasts.
--
-- One row per forecast run. The default model is a dependency-free logistic-
-- regression baseline trained on each symbol's own price history. Trained
-- scikit-learn / XGBoost / LightGBM or deep (LSTM/GRU/TFT) models implement the
-- same PredictionModelContract and can be swapped in without a schema change.
