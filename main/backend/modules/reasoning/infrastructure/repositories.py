from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.modules.reasoning.domain.entities import ReasonedOpinion, Stance
from backend.modules.reasoning.domain.repositories import ReasonedOpinionRepository
from backend.modules.reasoning.infrastructure.models import ReasonedOpinionModel


class InMemoryReasonedOpinionRepository(ReasonedOpinionRepository):
    """List-backed store for tests and offline development."""

    def __init__(self) -> None:
        self._opinions: list[ReasonedOpinion] = []

    async def save(self, opinion: ReasonedOpinion) -> None:
        self._opinions.append(opinion)

    async def get_latest(self, symbol: str) -> ReasonedOpinion | None:
        matches = [o for o in self._opinions if o.symbol == symbol]
        return max(matches, key=lambda o: o.as_of) if matches else None

    async def list_latest(self, limit: int = 50) -> list[ReasonedOpinion]:
        latest_by_symbol: dict[str, ReasonedOpinion] = {}
        for opinion in self._opinions:
            current = latest_by_symbol.get(opinion.symbol)
            if current is None or opinion.as_of > current.as_of:
                latest_by_symbol[opinion.symbol] = opinion
        ordered = sorted(latest_by_symbol.values(), key=lambda o: o.as_of, reverse=True)
        return ordered[:limit]


class SqlReasonedOpinionRepository(ReasonedOpinionRepository):
    """SQLAlchemy-backed reasoned-opinion repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, opinion: ReasonedOpinion) -> None:
        self._session.add(
            ReasonedOpinionModel(
                symbol=opinion.symbol,
                as_of=opinion.as_of,
                stance=opinion.stance.value,
                headline=opinion.headline,
                explanation=opinion.explanation,
                confidence=opinion.confidence,
                drivers=list(opinion.drivers),
                citations=list(opinion.citations),
                source=opinion.source,
                created_at=opinion.created_at,
            )
        )
        await self._session.flush()

    async def get_latest(self, symbol: str) -> ReasonedOpinion | None:
        stmt = (
            select(ReasonedOpinionModel)
            .where(ReasonedOpinionModel.symbol == symbol)
            .order_by(desc(ReasonedOpinionModel.as_of))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_latest(self, limit: int = 50) -> list[ReasonedOpinion]:
        stmt = (
            select(ReasonedOpinionModel)
            .order_by(desc(ReasonedOpinionModel.as_of))
            .limit(limit * 20)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        latest_by_symbol: dict[str, ReasonedOpinionModel] = {}
        for model in models:
            if model.symbol not in latest_by_symbol:
                latest_by_symbol[model.symbol] = model

        entities = [self._to_entity(m) for m in latest_by_symbol.values()]
        entities.sort(key=lambda o: o.as_of, reverse=True)
        return entities[:limit]

    def _to_entity(self, model: ReasonedOpinionModel) -> ReasonedOpinion:
        return ReasonedOpinion(
            symbol=model.symbol,
            as_of=self._ensure_aware(model.as_of),
            stance=Stance(model.stance),
            headline=model.headline,
            explanation=model.explanation,
            confidence=model.confidence,
            drivers=tuple(model.drivers or ()),
            citations=tuple(model.citations or ()),
            source=model.source,
            created_at=self._ensure_aware(model.created_at),
        )

    def _ensure_aware(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
