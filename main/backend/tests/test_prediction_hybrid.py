from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from backend.modules.prediction.application.dto import ForecastRequest
from backend.modules.prediction.application.services import PredictionService
from backend.modules.prediction.domain.entities import PredictionDirection
from backend.modules.prediction.infrastructure.ensemble import (
    EnsemblePredictor,
    WeightedModel,
    build_default_ensemble,
)
from backend.modules.prediction.infrastructure.predictors import LogisticBaselineModel
from backend.modules.prediction.infrastructure.repositories import (
    InMemoryPredictionRepository,
)
from backend.modules.prediction.infrastructure.timeseries import (
    Ar1Model,
    EwmaDriftModel,
)


def _trend(n: int, daily_drift: float, wobble: float = 0.0, start: float = 100.0):
    """Deterministic price path with a known drift."""
    return [
        start * math.exp(daily_drift * i) * (1.0 + wobble * math.sin(i * 0.7))
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Time-series models
# ---------------------------------------------------------------------------


def test_ewma_detects_an_uptrend_and_scales_with_horizon() -> None:
    model = EwmaDriftModel()
    prices = _trend(300, daily_drift=0.001, wobble=0.004)

    one_day = model.predict(prices, horizon_days=1)
    one_month = model.predict(prices, horizon_days=21)

    assert one_day.direction == PredictionDirection.UP
    assert one_day.probability_up > 0.5
    # Drift grows linearly with horizon while dispersion grows with its square
    # root, so a persistent trend reads as more certain over a longer horizon.
    assert one_month.probability_up > one_day.probability_up
    assert one_month.expected_return_pct > one_day.expected_return_pct
    assert one_day.features["ewma_daily_drift"] > 0


def test_ewma_detects_a_downtrend() -> None:
    result = EwmaDriftModel().predict(
        _trend(300, daily_drift=-0.0012, wobble=0.004), horizon_days=5
    )

    assert result.direction == PredictionDirection.DOWN
    assert result.probability_up < 0.5
    assert result.expected_return_pct < 0


def test_ewma_weights_recent_data_more_heavily() -> None:
    """A trend reversal near the end must dominate the older history."""
    model = EwmaDriftModel(decay=0.90)
    # 200 days up, then 60 days down.
    prices = _trend(200, daily_drift=0.002)
    tail_start = prices[-1]
    prices += [tail_start * math.exp(-0.003 * i) for i in range(1, 61)]

    result = model.predict(prices, horizon_days=5)

    assert result.features["ewma_daily_drift"] < 0  # follows the recent regime


def test_ar1_recovers_a_known_mean_reverting_slope() -> None:
    """Alternating returns are strongly negatively autocorrelated."""
    prices = [100.0]
    for i in range(300):
        prices.append(prices[-1] * (1.01 if i % 2 == 0 else 1 / 1.01))

    result = Ar1Model().predict(prices, horizon_days=1)

    # Perfect alternation -> slope close to -1 (reversal).
    assert result.features["ar1_slope"] < -0.8


def test_ar1_rejects_an_explosive_fit() -> None:
    """A near-unit-root fit must fall back, not extrapolate."""
    prices = [100.0 * (1.02**i) for i in range(200)]  # perfectly smooth compounding

    result = Ar1Model().predict(prices, horizon_days=10)

    assert abs(result.features["ar1_slope"]) < 0.999
    assert math.isfinite(result.expected_return_pct)


def test_time_series_models_decline_on_thin_history() -> None:
    thin = [100.0, 101.0, 102.0]

    for model in (EwmaDriftModel(), Ar1Model()):
        result = model.predict(thin, horizon_days=1)
        assert result.direction == PredictionDirection.NEUTRAL
        assert result.probability_up == 0.5
        assert result.confidence == 0.0


def test_models_are_deterministic() -> None:
    prices = _trend(300, 0.001, wobble=0.005)

    for model in (EwmaDriftModel(), Ar1Model(), LogisticBaselineModel()):
        first = model.predict(prices, horizon_days=5)
        second = model.predict(prices, horizon_days=5)
        assert first.probability_up == second.probability_up
        assert first.expected_return_pct == second.expected_return_pct


# ---------------------------------------------------------------------------
# Ensemble
# ---------------------------------------------------------------------------


def test_ensemble_combines_members_and_reports_their_contributions() -> None:
    ensemble = build_default_ensemble()
    prices = _trend(400, daily_drift=0.0012, wobble=0.005)

    result = ensemble.predict(prices, horizon_days=5)

    assert result.direction == PredictionDirection.UP
    # Every member is accounted for, present or not.
    assert result.features["ewma-drift-v1_available"] == 1.0
    assert result.features["ar1-v1_available"] == 1.0
    assert "logistic-baseline-v1_available" in result.features
    assert result.features["model_coverage"] > 0.0
    assert 0.0 <= result.confidence <= 1.0


def test_event_score_tilts_the_forecast_in_the_right_direction() -> None:
    ensemble = build_default_ensemble()
    prices = _trend(400, daily_drift=0.0002, wobble=0.006)  # near-flat: tiltable

    neutral = ensemble.predict(prices, horizon_days=5, event_score=0.0)
    good_news = ensemble.predict(prices, horizon_days=5, event_score=1.0)
    bad_news = ensemble.predict(prices, horizon_days=5, event_score=-1.0)

    assert good_news.probability_up > neutral.probability_up > bad_news.probability_up
    assert good_news.features["event_tilt_logodds"] > 0
    assert bad_news.features["event_tilt_logodds"] < 0


def test_event_tilt_is_bounded_and_cannot_overrule_the_price_models() -> None:
    """News shades a forecast; it must not manufacture one."""
    ensemble = build_default_ensemble()
    falling = _trend(400, daily_drift=-0.003, wobble=0.004)

    with_hype = ensemble.predict(falling, horizon_days=5, event_score=1.0)

    # Even maximally positive news cannot flip a strong downtrend to a buy.
    assert with_hype.probability_up < 0.5
    assert with_hype.direction != PredictionDirection.UP
    # Out-of-range scores are clamped rather than trusted.
    clamped = ensemble.predict(falling, horizon_days=5, event_score=99.0)
    assert clamped.features["event_score"] == 1.0


def test_ensemble_excludes_members_without_data_and_lowers_confidence() -> None:
    ensemble = build_default_ensemble()
    # Long enough for the time-series models, too short for the classifier's
    # windowed features to train.
    short = _trend(45, daily_drift=0.002, wobble=0.003)

    result = ensemble.predict(short, horizon_days=3)

    assert result.features["logistic-baseline-v1_available"] == 0.0
    # Coverage below 1.0 means confidence is discounted, not silently full.
    assert result.features["model_coverage"] < 1.0


def test_ensemble_returns_neutral_when_no_member_can_speak() -> None:
    result = build_default_ensemble().predict([100.0, 101.0], horizon_days=1)

    assert result.direction == PredictionDirection.NEUTRAL
    assert result.probability_up == 0.5
    assert result.confidence == 0.0


def test_ensemble_survives_a_broken_member() -> None:
    class _Exploding(LogisticBaselineModel):
        name = "exploding"

        def predict(self, closes, horizon_days=1, event_score=0.0):
            raise RuntimeError("model blew up")

    ensemble = EnsemblePredictor(
        [
            WeightedModel(_Exploding(), weight=0.5),
            WeightedModel(EwmaDriftModel(), weight=0.5),
        ]
    )

    result = ensemble.predict(_trend(300, 0.0015, wobble=0.004), horizon_days=5)

    # The healthy member still produces a forecast.
    assert result.confidence > 0.0
    assert result.direction == PredictionDirection.UP


def test_ensemble_rejects_an_empty_member_list() -> None:
    with pytest.raises(ValueError, match="at least one member"):
        EnsemblePredictor([])


# ---------------------------------------------------------------------------
# Multi-horizon service
# ---------------------------------------------------------------------------


@dataclass
class _FakePoint:
    timestamp: datetime
    close_price: str


@dataclass
class _FakeSeries:
    symbol: str
    currency: str
    prices: tuple[_FakePoint, ...]


class _FakeMarketData:
    def __init__(self, closes: list[float]) -> None:
        self._closes = closes

    async def get_historical_prices(self, request) -> _FakeSeries:
        start = datetime.now(UTC) - timedelta(days=len(self._closes))
        return _FakeSeries(
            symbol=request.symbol,
            currency="INR",
            prices=tuple(
                _FakePoint(start + timedelta(days=i), str(price))
                for i, price in enumerate(self._closes)
            ),
        )


class _FakeEvent:
    def __init__(self, sentiment: str, importance: str) -> None:
        self.sentiment = type("S", (), {"value": sentiment})()
        self.importance = type("I", (), {"value": importance})()


class _FakeEventRepository:
    def __init__(self, events: list[_FakeEvent]) -> None:
        self._events = events

    async def list_events(self, symbol=None, limit=50):
        return self._events


def _service(closes: list[float], events: list[_FakeEvent] | None = None):
    return PredictionService(
        market_data_service=_FakeMarketData(closes),
        model=build_default_ensemble(),
        repository=InMemoryPredictionRepository(),
        event_repository=(
            _FakeEventRepository(events) if events is not None else None
        ),
    )


@pytest.mark.asyncio
async def test_forecast_returns_one_entry_per_horizon_sorted() -> None:
    service = _service(_trend(400, 0.001, wobble=0.005))

    result = await service.forecast(
        ForecastRequest(symbol="test", horizons=(21, 1, 5))
    )

    assert result.symbol == "TEST"
    assert [f.horizon_days for f in result.forecasts] == [1, 5, 21]
    assert result.model_name == "hybrid-ensemble-v1"
    assert result.observations == 400
    assert all(0.0 <= f.probability_up <= 1.0 for f in result.forecasts)


@pytest.mark.asyncio
async def test_forecast_horizons_are_deduplicated_clamped_and_capped() -> None:
    service = _service(_trend(400, 0.001, wobble=0.005))

    result = await service.forecast(
        ForecastRequest(
            symbol="test",
            horizons=(5, 5, 0, -3, 9999, 1, 2, 3, 4, 7, 8),
        )
    )

    horizons = [f.horizon_days for f in result.forecasts]
    assert horizons == sorted(set(horizons))  # deduplicated and ordered
    assert min(horizons) >= 1  # zero and negatives clamped up
    assert max(horizons) <= 252  # absurd horizons clamped down
    assert len(horizons) <= 6  # capped


@pytest.mark.asyncio
async def test_forecast_folds_in_the_event_score() -> None:
    prices = _trend(400, 0.0002, wobble=0.006)
    positive_news = [_FakeEvent("positive", "high") for _ in range(3)]

    with_news = await _service(prices, positive_news).forecast(
        ForecastRequest(symbol="test", horizons=(5,))
    )
    without_news = await _service(prices, positive_news).forecast(
        ForecastRequest(symbol="test", horizons=(5,), include_events=False)
    )

    assert with_news.event_score == 1.0
    assert with_news.event_count == 3
    assert without_news.event_score == 0.0
    assert (
        with_news.forecasts[0].probability_up > without_news.forecasts[0].probability_up
    )


@pytest.mark.asyncio
async def test_forecast_without_an_event_repository_is_price_only() -> None:
    result = await _service(_trend(300, 0.001, wobble=0.004)).forecast(
        ForecastRequest(symbol="test", horizons=(1, 5))
    )

    assert result.event_score == 0.0
    assert result.event_count == 0
    assert len(result.forecasts) == 2


@pytest.mark.asyncio
async def test_mixed_news_nets_out_to_a_small_score() -> None:
    mixed = [_FakeEvent("positive", "high"), _FakeEvent("negative", "high")]
    service = _service(_trend(300, 0.0005, wobble=0.004), mixed)

    result = await service.forecast(ForecastRequest(symbol="test", horizons=(5,)))

    assert result.event_score == pytest.approx(0.0, abs=1e-6)
    assert result.event_count == 2
