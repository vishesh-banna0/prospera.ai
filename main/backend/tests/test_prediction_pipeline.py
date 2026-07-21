from __future__ import annotations

import math
from datetime import UTC, datetime

import pytest

from backend.modules.market_data.application.dto import (
    HistoricalPricePointView,
    HistoricalPriceSeriesView,
)
from backend.modules.prediction.application.dto import PredictRequest
from backend.modules.prediction.application.services import PredictionService
from backend.modules.prediction.domain.entities import PredictionDirection
from backend.modules.prediction.domain.features import build_dataset, feature_vector
from backend.modules.prediction.infrastructure.predictors import LogisticBaselineModel
from backend.modules.prediction.infrastructure.repositories import (
    InMemoryPredictionRepository,
)


def test_feature_vector_and_dataset_shapes() -> None:
    closes = [100.0 + i for i in range(60)]
    vec = feature_vector(closes, len(closes) - 1)
    assert len(vec) == 6

    x, y, latest = build_dataset(closes, horizon=1)
    assert len(x) == len(y) > 0
    assert latest is not None and len(latest) == 6
    # On a strict uptrend, every next-day label is "up".
    assert set(y) == {1}


def test_model_is_neutral_without_enough_history() -> None:
    model = LogisticBaselineModel()
    out = model.predict([100.0, 101.0, 102.0], horizon_days=1)
    assert out.direction == PredictionDirection.NEUTRAL
    assert out.probability_up == pytest.approx(0.5)
    assert out.confidence == pytest.approx(0.0)


def test_model_is_deterministic_and_bounded() -> None:
    # A trend with mild noise gives the classifier both up and down days.
    closes = [100.0 * (1.01**i) + 3.0 * math.sin(i) for i in range(120)]
    model = LogisticBaselineModel()
    out1 = model.predict(closes, horizon_days=1)
    out2 = model.predict(closes, horizon_days=1)

    assert out1 == out2  # deterministic
    assert 0.0 <= out1.probability_up <= 1.0
    assert 0.0 <= out1.confidence <= 1.0
    assert out1.direction in set(PredictionDirection)
    assert set(out1.features.keys())  # features recorded


class _StubMarketData:
    def __init__(self, closes: list[float]) -> None:
        self._closes = closes

    async def get_historical_prices(self, request):
        prices = tuple(
            HistoricalPricePointView(
                timestamp=datetime(2026, 1, 1, tzinfo=UTC),
                open_price=str(c),
                high_price=str(c),
                low_price=str(c),
                close_price=str(c),
                volume=1000,
            )
            for c in self._closes
        )
        return HistoricalPriceSeriesView(
            symbol=request.symbol, currency="INR", prices=prices
        )


@pytest.mark.asyncio
async def test_prediction_service_predict_and_retrieve() -> None:
    closes = [100.0 * (1.008**i) + 2.0 * math.sin(i / 2) for i in range(150)]
    repo = InMemoryPredictionRepository()
    service = PredictionService(
        market_data_service=_StubMarketData(closes),
        model=LogisticBaselineModel(),
        repository=repo,
    )

    view = await service.predict(PredictRequest(symbol="aaa", lookback_days=365))
    assert view.symbol == "AAA"
    assert view.model_name == "logistic-baseline-v1"
    assert 0.0 <= view.probability_up <= 1.0

    latest = await service.get_latest("AAA")
    assert latest.prediction_id == view.prediction_id

    listing = await service.list_latest()
    assert listing.count == 1


@pytest.mark.asyncio
async def test_prediction_service_neutral_when_offline() -> None:
    class FailingMarketData:
        async def get_historical_prices(self, request):
            raise RuntimeError("no api key")

    service = PredictionService(
        market_data_service=FailingMarketData(),
        model=LogisticBaselineModel(),
        repository=InMemoryPredictionRepository(),
    )
    view = await service.predict(PredictRequest(symbol="ZZZ"))
    assert view.direction == PredictionDirection.NEUTRAL.value
    assert view.probability_up == pytest.approx(0.5)
