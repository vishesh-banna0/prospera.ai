from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class PredictRequest:
    symbol: str
    lookback_days: int = 365
    horizon_days: int = 1


@dataclass(frozen=True, slots=True)
class PredictionView:
    prediction_id: str
    symbol: str
    as_of: datetime
    horizon_days: int
    direction: str
    probability_up: float
    expected_return_pct: float
    confidence: float
    model_name: str
    features: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PredictionsView:
    predictions: tuple[PredictionView, ...]
    count: int


# Purpose:
# Application-layer request/response contracts for Phase 12 predictions.
