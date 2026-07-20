from __future__ import annotations

from datetime import UTC
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.modules.events.domain.entities import (
    EventImportance,
    EventType,
    NewsEvent,
    Sentiment,
)
from backend.modules.events.domain.repositories import NewsEventRepository
from backend.modules.events.infrastructure.models import NewsEventModel


class InMemoryNewsEventRepository(NewsEventRepository):
    """Dict-backed event store for tests and offline development."""

    def __init__(self) -> None:
        self._events: dict[str, NewsEvent] = {}

    async def upsert_events(
        self,
        events: list[NewsEvent],
    ) -> int:
        for event in events:
            self._events[event.event_id] = event
        return len(events)

    async def list_events(
        self,
        event_type: EventType | None = None,
        symbol: str | None = None,
        sector: str | None = None,
        sentiment: Sentiment | None = None,
        importance: EventImportance | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[NewsEvent]:
        events = sorted(
            self._events.values(),
            key=lambda event: event.event_date,
            reverse=True,
        )
        filtered = [
            event
            for event in events
            if self._matches(
                event,
                event_type,
                symbol,
                sector,
                sentiment,
                importance,
                start_at,
                end_at,
            )
        ]
        return filtered[offset : offset + limit]

    async def get_event(
        self,
        event_id: str,
    ) -> NewsEvent | None:
        return self._events.get(event_id)

    async def get_stats(
        self,
    ) -> dict[str, int]:
        stats: dict[str, int] = {"total": len(self._events)}
        for event in self._events.values():
            key = event.event_type.value
            stats[key] = stats.get(key, 0) + 1
        return stats

    def _matches(
        self,
        event: NewsEvent,
        event_type: EventType | None,
        symbol: str | None,
        sector: str | None,
        sentiment: Sentiment | None,
        importance: EventImportance | None,
        start_at: datetime | None,
        end_at: datetime | None,
    ) -> bool:
        if event_type is not None and event.event_type != event_type:
            return False
        if sentiment is not None and event.sentiment != sentiment:
            return False
        if importance is not None and event.importance != importance:
            return False
        if symbol is not None and symbol.upper() not in event.symbols:
            return False
        if sector is not None and sector.title() not in event.sectors:
            return False
        if start_at is not None and event.event_date < start_at:
            return False
        if end_at is not None and event.event_date > end_at:
            return False
        return True


class SqlNewsEventRepository(NewsEventRepository):
    """SQLAlchemy-backed implementation of the event repository contract.

    Event type, sentiment, importance, and date range are filtered in SQL.
    Symbol/sector membership is filtered in Python because those are JSON
    array columns (the same approach the news warehouse uses); a Postgres
    deployment can later push these into GIN-indexed containment queries.
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def upsert_events(
        self,
        events: list[NewsEvent],
    ) -> int:
        for event in events:
            stmt = select(NewsEventModel).where(
                NewsEventModel.event_id == event.event_id
            )
            result = await self._session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                self._session.add(self._entity_to_model(event))
                continue

            self._update_model(model, event)

        await self._session.flush()
        return len(events)

    async def list_events(
        self,
        event_type: EventType | None = None,
        symbol: str | None = None,
        sector: str | None = None,
        sentiment: Sentiment | None = None,
        importance: EventImportance | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[NewsEvent]:
        stmt = select(NewsEventModel)
        if event_type is not None:
            stmt = stmt.where(NewsEventModel.event_type == event_type.value)
        if sentiment is not None:
            stmt = stmt.where(NewsEventModel.sentiment == sentiment.value)
        if importance is not None:
            stmt = stmt.where(NewsEventModel.importance == importance.value)
        if start_at is not None:
            stmt = stmt.where(NewsEventModel.event_date >= start_at)
        if end_at is not None:
            stmt = stmt.where(NewsEventModel.event_date <= end_at)

        stmt = stmt.order_by(NewsEventModel.event_date.desc())
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        events = [self._model_to_entity(model) for model in models]
        filtered = [
            event
            for event in events
            if self._matches_array_filters(event, symbol, sector)
        ]
        return filtered[offset : offset + limit]

    async def get_event(
        self,
        event_id: str,
    ) -> NewsEvent | None:
        stmt = select(NewsEventModel).where(NewsEventModel.event_id == event_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._model_to_entity(model)

    async def get_stats(
        self,
    ) -> dict[str, int]:
        total_result = await self._session.execute(
            select(func.count()).select_from(NewsEventModel)
        )
        stats = {"total": int(total_result.scalar_one() or 0)}

        type_result = await self._session.execute(
            select(NewsEventModel.event_type, func.count()).group_by(
                NewsEventModel.event_type
            )
        )
        for event_type, count in type_result.all():
            stats[str(event_type)] = int(count)
        return stats

    def _matches_array_filters(
        self,
        event: NewsEvent,
        symbol: str | None,
        sector: str | None,
    ) -> bool:
        if symbol is not None and symbol.upper() not in event.symbols:
            return False
        if sector is not None and sector.title() not in event.sectors:
            return False
        return True

    def _entity_to_model(
        self,
        event: NewsEvent,
    ) -> NewsEventModel:
        return NewsEventModel(
            event_id=event.event_id,
            article_id=event.article_id,
            event_type=event.event_type.value,
            sentiment=event.sentiment.value,
            importance=event.importance.value,
            headline=event.headline,
            summary=event.summary,
            symbols=list(event.symbols),
            sectors=list(event.sectors),
            keywords=list(event.keywords),
            confidence=event.confidence,
            source=event.source,
            event_date=event.event_date,
            created_at=event.created_at,
        )

    def _update_model(
        self,
        model: NewsEventModel,
        event: NewsEvent,
    ) -> None:
        model.article_id = event.article_id
        model.event_type = event.event_type.value
        model.sentiment = event.sentiment.value
        model.importance = event.importance.value
        model.headline = event.headline
        model.summary = event.summary
        model.symbols = list(event.symbols)
        model.sectors = list(event.sectors)
        model.keywords = list(event.keywords)
        model.confidence = event.confidence
        model.source = event.source
        model.event_date = event.event_date
        model.created_at = event.created_at

    def _model_to_entity(
        self,
        model: NewsEventModel,
    ) -> NewsEvent:
        return NewsEvent(
            event_id=model.event_id,
            article_id=model.article_id,
            event_type=EventType(model.event_type),
            sentiment=Sentiment(model.sentiment),
            importance=EventImportance(model.importance),
            headline=model.headline,
            summary=model.summary,
            symbols=tuple(model.symbols or ()),
            sectors=tuple(model.sectors or ()),
            keywords=tuple(model.keywords or ()),
            confidence=float(model.confidence),
            source=model.source,
            event_date=self._ensure_aware(model.event_date),
            created_at=self._ensure_aware(model.created_at),
        )

    def _ensure_aware(
        self,
        value: datetime,
    ) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
