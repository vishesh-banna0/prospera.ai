from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.modules.company.domain.entities import CompanyRating, CompanyScore
from backend.modules.company.domain.repositories import CompanyScoreRepository
from backend.modules.company.infrastructure.models import CompanyScoreModel


class InMemoryCompanyScoreRepository(CompanyScoreRepository):
    """Dict-backed store for tests and offline development."""

    def __init__(self) -> None:
        # Keep full history; the latest per symbol is derived by as_of.
        self._scores: list[CompanyScore] = []

    async def save(self, score: CompanyScore) -> None:
        self._scores.append(score)

    async def get_latest(self, symbol: str) -> CompanyScore | None:
        matches = [s for s in self._scores if s.symbol == symbol]
        if not matches:
            return None
        return max(matches, key=lambda s: s.as_of)

    async def list_latest(self, limit: int = 50) -> list[CompanyScore]:
        latest_by_symbol: dict[str, CompanyScore] = {}
        for score in self._scores:
            current = latest_by_symbol.get(score.symbol)
            if current is None or score.as_of > current.as_of:
                latest_by_symbol[score.symbol] = score
        ordered = sorted(
            latest_by_symbol.values(),
            key=lambda s: s.overall_score,
            reverse=True,
        )
        return ordered[:limit]


class SqlCompanyScoreRepository(CompanyScoreRepository):
    """SQLAlchemy-backed company score repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, score: CompanyScore) -> None:
        self._session.add(
            CompanyScoreModel(
                symbol=score.symbol,
                as_of=score.as_of,
                overall_score=score.overall_score,
                growth_score=score.growth_score,
                risk_score=score.risk_score,
                sentiment_score=score.sentiment_score,
                rating=score.rating.value,
                company_name=score.company_name,
                sector=score.sector,
                market_cap=score.market_cap,
                event_count=score.event_count,
                price_points=score.price_points,
                rationale=list(score.rationale),
                source=score.source,
                created_at=score.created_at,
            )
        )
        await self._session.flush()

    async def get_latest(self, symbol: str) -> CompanyScore | None:
        stmt = (
            select(CompanyScoreModel)
            .where(CompanyScoreModel.symbol == symbol)
            .order_by(desc(CompanyScoreModel.as_of))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_latest(self, limit: int = 50) -> list[CompanyScore]:
        # Pull the most recent rows and reduce to the latest per symbol in
        # Python (portable across SQLite/Postgres without window functions).
        stmt = (
            select(CompanyScoreModel)
            .order_by(desc(CompanyScoreModel.as_of))
            .limit(limit * 20)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        latest_by_symbol: dict[str, CompanyScoreModel] = {}
        for model in models:
            if model.symbol not in latest_by_symbol:
                latest_by_symbol[model.symbol] = model

        entities = [self._to_entity(model) for model in latest_by_symbol.values()]
        entities.sort(key=lambda s: s.overall_score, reverse=True)
        return entities[:limit]

    def _to_entity(self, model: CompanyScoreModel) -> CompanyScore:
        return CompanyScore(
            symbol=model.symbol,
            as_of=self._ensure_aware(model.as_of),
            overall_score=model.overall_score,
            growth_score=model.growth_score,
            risk_score=model.risk_score,
            sentiment_score=model.sentiment_score,
            rating=CompanyRating(model.rating),
            company_name=model.company_name,
            sector=model.sector,
            market_cap=model.market_cap,
            event_count=model.event_count,
            price_points=model.price_points,
            rationale=tuple(model.rationale or ()),
            source=model.source,
            created_at=self._ensure_aware(model.created_at),
        )

    def _ensure_aware(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
