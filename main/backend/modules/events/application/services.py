from __future__ import annotations

from collections.abc import Awaitable
from collections.abc import Callable
from datetime import UTC
from datetime import datetime
from typing import Iterable

from backend.modules.events.application.dto import (
    EventQueryRequest,
    EventStatsView,
    EventTypeCount,
    EventView,
    EventsView,
    ExtractEventsRequest,
    ExtractEventsView,
)
from backend.modules.events.application.extractors import EventExtractorContract
from backend.modules.events.domain.entities import (
    EventImportance,
    EventType,
    NewsEvent,
    Sentiment,
)
from backend.modules.events.domain.repositories import NewsEventRepository
from backend.modules.news.domain.entities import NewsArticle
from backend.modules.news.domain.entities import NewsCategory
from backend.modules.news.domain.repositories import NewsArticleRepository


class EventExtractionService:
    """Phase 8 application boundary.

    Pipeline: ``select articles -> extract -> deduplicate -> store``.

    Reads articles from the Phase 7 news warehouse (through the
    ``NewsArticleRepository`` port) and writes structured events through the
    ``NewsEventRepository`` port. The extraction strategy itself is injected
    as an ``EventExtractorContract`` so it can be swapped without touching
    this orchestration.
    """

    def __init__(
        self,
        article_repository: NewsArticleRepository,
        event_repository: NewsEventRepository,
        extractor: EventExtractorContract | None = None,
        commit: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self._article_repository = article_repository
        self._event_repository = event_repository
        self._extractor = extractor
        self._commit = commit

    async def extract_events(
        self,
        request: ExtractEventsRequest,
    ) -> ExtractEventsView:
        if self._extractor is None:
            return ExtractEventsView(
                processed_count=0,
                extracted_count=0,
                stored_count=0,
                message="No event extractor is configured.",
            )

        articles = await self._select_articles(request)

        extracted: list[NewsEvent] = []
        for article in articles:
            extracted.extend(await self._extractor.extract_events(article))

        deduplicated = self._deduplicate(extracted)
        stored_count = await self._event_repository.upsert_events(deduplicated)

        if self._commit is not None:
            await self._commit()

        return ExtractEventsView(
            processed_count=len(articles),
            extracted_count=len(extracted),
            stored_count=stored_count,
        )

    async def list_events(
        self,
        request: EventQueryRequest,
    ) -> EventsView:
        limit = self._normalize_limit(request.limit)
        offset = max(0, request.offset)

        events = await self._event_repository.list_events(
            event_type=self._optional_event_type(request.event_type),
            symbol=self._optional_upper(request.symbol),
            sector=self._optional_title(request.sector),
            sentiment=self._optional_sentiment(request.sentiment),
            importance=self._optional_importance(request.importance),
            start_at=self._normalize_datetime(request.start_at),
            end_at=self._normalize_datetime(request.end_at),
            limit=limit,
            offset=offset,
        )

        return EventsView(
            events=tuple(self._to_view(event) for event in events),
            count=len(events),
            limit=limit,
            offset=offset,
        )

    async def get_event(
        self,
        event_id: str,
    ) -> EventView:
        event = await self._event_repository.get_event(event_id)
        if event is None:
            raise ValueError(f"News event '{event_id}' was not found.")
        return self._to_view(event)

    async def get_stats(
        self,
    ) -> EventStatsView:
        stats = await self._event_repository.get_stats()
        total = stats.get("total", 0)
        by_type = tuple(
            EventTypeCount(event_type=event_type.value, count=stats[event_type.value])
            for event_type in EventType
            if stats.get(event_type.value, 0) > 0
        )
        by_type = tuple(sorted(by_type, key=lambda item: item.count, reverse=True))
        return EventStatsView(total_events=total, by_type=by_type)

    async def _select_articles(
        self,
        request: ExtractEventsRequest,
    ) -> list[NewsArticle]:
        if request.article_ids:
            selected: list[NewsArticle] = []
            for article_id in request.article_ids:
                article = await self._article_repository.get_article(article_id)
                if article is not None:
                    selected.append(article)
            return selected

        return await self._article_repository.list_articles(
            category=self._optional_category(request.category),
            symbol=self._optional_upper(request.symbol),
            sector=self._optional_title(request.sector),
            query=self._optional_text(request.query),
            limit=self._normalize_limit(request.limit),
        )

    def _deduplicate(
        self,
        events: Iterable[NewsEvent],
    ) -> list[NewsEvent]:
        seen: set[str] = set()
        unique: list[NewsEvent] = []
        for event in events:
            if event.event_id in seen:
                continue
            seen.add(event.event_id)
            unique.append(event)
        return unique

    def _optional_category(
        self,
        raw_category: str | None,
    ) -> NewsCategory | None:
        if raw_category is None or not str(raw_category).strip():
            return None
        return NewsCategory(str(raw_category).strip().lower())

    def _optional_event_type(
        self,
        raw_event_type: str | None,
    ) -> EventType | None:
        if raw_event_type is None or not str(raw_event_type).strip():
            return None
        return EventType(str(raw_event_type).strip().lower())

    def _optional_sentiment(
        self,
        raw_sentiment: str | None,
    ) -> Sentiment | None:
        if raw_sentiment is None or not str(raw_sentiment).strip():
            return None
        return Sentiment(str(raw_sentiment).strip().lower())

    def _optional_importance(
        self,
        raw_importance: str | None,
    ) -> EventImportance | None:
        if raw_importance is None or not str(raw_importance).strip():
            return None
        return EventImportance(str(raw_importance).strip().lower())

    def _normalize_limit(
        self,
        limit: int,
    ) -> int:
        return min(max(1, int(limit)), 200)

    def _normalize_datetime(
        self,
        value: datetime | None,
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

    def _optional_text(
        self,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None
        clean = value.strip()
        return clean or None

    def _optional_upper(
        self,
        value: str | None,
    ) -> str | None:
        clean = self._optional_text(value)
        return clean.upper() if clean is not None else None

    def _optional_title(
        self,
        value: str | None,
    ) -> str | None:
        clean = self._optional_text(value)
        return clean.title() if clean is not None else None

    def _to_view(
        self,
        event: NewsEvent,
    ) -> EventView:
        return EventView(
            event_id=event.event_id,
            article_id=event.article_id,
            event_type=event.event_type.value,
            sentiment=event.sentiment.value,
            importance=event.importance.value,
            headline=event.headline,
            event_date=event.event_date,
            summary=event.summary,
            symbols=event.symbols,
            sectors=event.sectors,
            keywords=event.keywords,
            confidence=event.confidence,
            source=event.source,
            created_at=event.created_at,
        )
