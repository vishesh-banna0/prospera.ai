from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from backend.modules.market_data.application.dto import HistoricalPriceRequest
from backend.modules.prediction.application.dto import (
    ForecastRequest,
    HorizonForecastView,
    MultiHorizonForecastView,
    PredictionsView,
    PredictionView,
    PredictRequest,
)
from backend.modules.prediction.application.models import PredictionModelContract
from backend.modules.prediction.domain.entities import Prediction
from backend.modules.prediction.domain.repositories import PredictionRepository

logger = logging.getLogger(__name__)

# How a news event maps onto a [-1, 1] score. Mirrors the weighting the signal
# fusion layer uses, so the two layers agree on what "positive news" means.
_SENTIMENT_SIGN = {"positive": 1.0, "negative": -1.0, "neutral": 0.0}
_IMPORTANCE_WEIGHT = {"high": 1.0, "medium": 0.6, "low": 0.3}

# Cap on horizons per request — each one is a separate model fit.
_MAX_HORIZONS = 6


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
        event_repository=None,
    ) -> None:
        self._market_data = market_data_service
        self._model = model
        self._repository = repository
        self._commit = commit
        self._events = event_repository

    async def predict(self, request: PredictRequest) -> PredictionView:
        symbol = request.symbol.strip().upper()
        horizon = max(1, int(request.horizon_days))
        closes = await self._load_closes(symbol, request.lookback_days)
        event_score, _ = await self._event_score(symbol)

        output = self._model.predict(
            closes, horizon_days=horizon, event_score=event_score
        )

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

    async def forecast(self, request: ForecastRequest) -> MultiHorizonForecastView:
        """Forecast one symbol across several horizons in a single pass.

        Each horizon is a separate model call — a 1-day and a 63-day forecast
        are genuinely different questions, not one number rescaled — but they
        share the loaded price history and the news score, so this costs one
        market-data round trip rather than one per horizon.
        """

        symbol = request.symbol.strip().upper()
        horizons = self._normalize_horizons(request.horizons)
        closes = await self._load_closes(symbol, request.lookback_days)

        event_score, event_count = (
            await self._event_score(symbol) if request.include_events else (0.0, 0)
        )

        forecasts: list[HorizonForecastView] = []
        features: dict[str, float] = {}
        for horizon in horizons:
            output = self._model.predict(
                closes, horizon_days=horizon, event_score=event_score
            )
            forecasts.append(
                HorizonForecastView(
                    horizon_days=horizon,
                    direction=output.direction.value,
                    probability_up=round(output.probability_up, 4),
                    expected_return_pct=round(output.expected_return_pct, 4),
                    confidence=round(output.confidence, 4),
                )
            )
            # Diagnostics from the shortest horizon are enough to show which
            # members contributed; repeating them per horizon adds noise.
            if not features:
                features = output.features

        return MultiHorizonForecastView(
            symbol=symbol,
            as_of=datetime.now(UTC),
            model_name=self._model.name,
            forecasts=tuple(forecasts),
            event_score=round(event_score, 4),
            event_count=event_count,
            observations=len(closes),
            features=features,
        )

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

    def _normalize_horizons(self, horizons: tuple[int, ...]) -> tuple[int, ...]:
        cleaned = sorted(
            {min(max(1, int(h)), 252) for h in (horizons or (1, 5, 21, 63))}
        )
        return tuple(cleaned[:_MAX_HORIZONS])

    async def _event_score(self, symbol: str) -> tuple[float, int]:
        """Recent news for the symbol as a single [-1, 1] score.

        Averaged rather than summed so a symbol with many articles does not
        automatically outweigh one with few — this measures the *tone* of
        recent coverage, not its volume. Returns (0.0, 0) when there is no
        event repository wired or no recent news, which makes the ensemble's
        news tilt vanish rather than guess.
        """

        if self._events is None:
            return 0.0, 0
        try:
            events = await self._events.list_events(symbol=symbol, limit=50)
        except Exception as exc:
            logger.warning("Event score unavailable for %s: %s", symbol, exc)
            return 0.0, 0

        if not events:
            return 0.0, 0

        scores = [
            _SENTIMENT_SIGN.get(getattr(e.sentiment, "value", ""), 0.0)
            * _IMPORTANCE_WEIGHT.get(getattr(e.importance, "value", ""), 0.5)
            for e in events
        ]
        return max(-1.0, min(1.0, sum(scores) / len(scores))), len(events)

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
