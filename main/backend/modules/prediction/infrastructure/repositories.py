from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.modules.prediction.domain.entities import Prediction, PredictionDirection
from backend.modules.prediction.domain.repositories import PredictionRepository
from backend.modules.prediction.infrastructure.models import PredictionModel


class InMemoryPredictionRepository(PredictionRepository):
    """List-backed store for tests and offline development."""

    def __init__(self) -> None:
        self._predictions: list[Prediction] = []

    async def save(self, prediction: Prediction) -> None:
        self._predictions.append(prediction)

    async def get_latest(self, symbol: str) -> Prediction | None:
        matches = [p for p in self._predictions if p.symbol == symbol]
        if not matches:
            return None
        return max(matches, key=lambda p: p.as_of)

    async def list_latest(self, limit: int = 50) -> list[Prediction]:
        latest_by_symbol: dict[str, Prediction] = {}
        for prediction in self._predictions:
            current = latest_by_symbol.get(prediction.symbol)
            if current is None or prediction.as_of > current.as_of:
                latest_by_symbol[prediction.symbol] = prediction
        ordered = sorted(
            latest_by_symbol.values(), key=lambda p: p.as_of, reverse=True
        )
        return ordered[:limit]


class SqlPredictionRepository(PredictionRepository):
    """SQLAlchemy-backed prediction repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, prediction: Prediction) -> None:
        self._session.add(
            PredictionModel(
                prediction_id=prediction.prediction_id,
                symbol=prediction.symbol,
                as_of=prediction.as_of,
                horizon_days=prediction.horizon_days,
                direction=prediction.direction.value,
                probability_up=prediction.probability_up,
                expected_return_pct=prediction.expected_return_pct,
                confidence=prediction.confidence,
                model_name=prediction.model_name,
                features=dict(prediction.features),
                created_at=prediction.created_at,
            )
        )
        await self._session.flush()

    async def get_latest(self, symbol: str) -> Prediction | None:
        stmt = (
            select(PredictionModel)
            .where(PredictionModel.symbol == symbol)
            .order_by(desc(PredictionModel.as_of))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_latest(self, limit: int = 50) -> list[Prediction]:
        stmt = (
            select(PredictionModel)
            .order_by(desc(PredictionModel.as_of))
            .limit(limit * 20)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        latest_by_symbol: dict[str, PredictionModel] = {}
        for model in models:
            if model.symbol not in latest_by_symbol:
                latest_by_symbol[model.symbol] = model

        entities = [self._to_entity(model) for model in latest_by_symbol.values()]
        entities.sort(key=lambda p: p.as_of, reverse=True)
        return entities[:limit]

    def _to_entity(self, model: PredictionModel) -> Prediction:
        return Prediction(
            prediction_id=model.prediction_id,
            symbol=model.symbol,
            as_of=self._ensure_aware(model.as_of),
            horizon_days=model.horizon_days,
            direction=PredictionDirection(model.direction),
            probability_up=model.probability_up,
            expected_return_pct=model.expected_return_pct,
            confidence=model.confidence,
            model_name=model.model_name,
            features=dict(model.features or {}),
            created_at=self._ensure_aware(model.created_at),
        )

    def _ensure_aware(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
