from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class PredictRequest:
    symbol: str
    lookback_days: int = 365
    horizon_days: int = 1


@dataclass(frozen=True, slots=True)
class ForecastRequest:
    """A multi-horizon forecast for one symbol.

    The default horizons are a trading week, a month, and a quarter of trading
    days. Reporting several at once is the honest presentation: forecast skill
    at 1 day is close to a coin flip and improves with horizon, so a single
    number invites over-reading whichever horizon happened to be chosen.
    """

    symbol: str
    lookback_days: int = 730
    horizons: tuple[int, ...] = (1, 5, 21, 63)
    # Recent events for the symbol tilt the blend. Set false for a
    # price-only forecast (useful for isolating the news contribution).
    include_events: bool = True


@dataclass(frozen=True, slots=True)
class HorizonForecastView:
    horizon_days: int
    direction: str
    probability_up: float
    expected_return_pct: float
    confidence: float


@dataclass(frozen=True, slots=True)
class MultiHorizonForecastView:
    symbol: str
    as_of: datetime
    model_name: str
    forecasts: tuple[HorizonForecastView, ...]
    # The news signal folded into the blend, in [-1, 1]; 0.0 when there was no
    # recent news or it netted out.
    event_score: float = 0.0
    event_count: int = 0
    observations: int = 0
    features: dict[str, float] = field(default_factory=dict)


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
