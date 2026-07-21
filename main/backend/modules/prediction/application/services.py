from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from backend.modules.market_data.application.dto import HistoricalPriceRequest
from backend.modules.prediction.application.dto import (
    PredictionsView,
    PredictionView,
    PredictRequest,
)
from backend.modules.prediction.application.models import PredictionModelContract
from backend.modules.prediction.domain.entities import Prediction
from backend.modules.prediction.domain.repositories import PredictionRepository

logger = logging.getLogger(__name__)


class PredictionService:
    """Phase 12 application boundary.

    Pipeline: ``load price history -> model.predict -> store forecast``. The
    model is injected as a ``PredictionModelContract`` so the baseline can be
    swapped for a trained model without touching this orchestration. Fully
    testable offline with a stub market data service.
    """

    def __init__(
        self,
        market_data_service,
        model: PredictionModelContract,
        repository: PredictionRepository,
        commit: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self._market_data = market_data_service
        self._model = model
        self._repository = repository
        self._commit = commit

    async def predict(self, request: PredictRequest) -> PredictionView:
        symbol = request.symbol.strip().upper()
        horizon = max(1, int(request.horizon_days))
        closes = await self._load_closes(symbol, request.lookback_days)

        output = self._model.predict(closes, horizon_days=horizon)

        prediction = Prediction(
            prediction_id=str(uuid.uuid4()),
            symbol=symbol,
            as_of=datetime.now(UTC),
            horizon_days=horizon,
            direction=output.direction,
            probability_up=output.probability_up,
            expected_return_pct=output.expected_return_pct,
            confidence=output.confidence,
            model_name=self._model.name,
            features=output.features,
        )

        await self._repository.save(prediction)
        if self._commit is not None:
            await self._commit()

        return self._to_view(prediction)

    async def get_latest(self, symbol: str) -> PredictionView:
        prediction = await self._repository.get_latest(symbol.strip().upper())
        if prediction is None:
            raise ValueError(f"No prediction found for '{symbol}'. Run predict first.")
        return self._to_view(prediction)

    async def list_latest(self, limit: int = 50) -> PredictionsView:
        limit = min(max(1, int(limit)), 200)
        predictions = await self._repository.list_latest(limit=limit)
        views = tuple(self._to_view(p) for p in predictions)
        return PredictionsView(predictions=views, count=len(views))

    async def _load_closes(self, symbol: str, lookback_days: int) -> list[float]:
        end_at = datetime.now(UTC)
        start_at = end_at - timedelta(days=max(1, lookback_days))
        try:
            series = await self._market_data.get_historical_prices(
                HistoricalPriceRequest(
                    symbol=symbol, start_at=start_at, end_at=end_at, auto_sync=True
                )
            )
        except Exception as exc:
            logger.warning("Price history unavailable for %s: %s", symbol, exc)
            return []

        closes: list[float] = []
        for point in series.prices:
            try:
                closes.append(float(point.close_price))
            except (TypeError, ValueError):
                continue
        return closes

    def _to_view(self, prediction: Prediction) -> PredictionView:
        return PredictionView(
            prediction_id=prediction.prediction_id,
            symbol=prediction.symbol,
            as_of=prediction.as_of,
            horizon_days=prediction.horizon_days,
            direction=prediction.direction.value,
            probability_up=prediction.probability_up,
            expected_return_pct=round(prediction.expected_return_pct, 4),
            confidence=round(prediction.confidence, 4),
            model_name=prediction.model_name,
            features=prediction.features,
        )
