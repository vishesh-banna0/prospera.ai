from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class PredictionDirection(StrEnum):
    """Predicted direction of the next move over the forecast horizon."""

    UP = "up"
    DOWN = "down"
    NEUTRAL = "neutral"


@dataclass(frozen=True, slots=True)
class ModelOutput:
    """What a prediction model returns for one symbol (no persistence concerns).

    Kept separate from the stored ``Prediction`` so a model implementation only
    has to produce these fields; the service adds identity/time/persistence.
    """

    direction: PredictionDirection
    probability_up: float
    expected_return_pct: float
    confidence: float
    features: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "probability_up", min(1.0, max(0.0, float(self.probability_up)))
        )
        object.__setattr__(self, "confidence", min(1.0, max(0.0, float(self.confidence))))


@dataclass(frozen=True, slots=True)
class Prediction:
    """A stored forecast: a model's output for a symbol at a point in time."""

    prediction_id: str
    symbol: str
    as_of: datetime
    horizon_days: int

    direction: PredictionDirection
    probability_up: float
    expected_return_pct: float
    confidence: float

    model_name: str
    features: dict[str, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("Prediction symbol cannot be blank.")
        if self.as_of.tzinfo is None:
            raise ValueError("Prediction as_of must be timezone aware.")
        if self.horizon_days < 1:
            raise ValueError("Prediction horizon_days must be >= 1.")


# Purpose:
# Define the Phase 12 output types: a model's raw output and a stored forecast.
#
# What Should Not Live Here:
# - Feature engineering (see features.py) or model math (infrastructure).
# - Persistence / HTTP.
