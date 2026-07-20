from __future__ import annotations

from datetime import UTC
from datetime import datetime

import pytest

from backend.modules.events.application.dto import EventQueryRequest
from backend.modules.events.application.dto import ExtractEventsRequest
from backend.modules.events.application.services import EventExtractionService
from backend.modules.events.domain.entities import EventImportance
from backend.modules.events.domain.entities import EventType
from backend.modules.events.domain.entities import Sentiment
from backend.modules.events.infrastructure.extractors import RuleBasedEventExtractor
from backend.modules.events.infrastructure.repositories import (
    InMemoryNewsEventRepository,
)
from backend.modules.news.domain.entities import NewsArticle
from backend.modules.news.domain.entities import NewsCategory
from backend.modules.news.infrastructure.repositories import (
    InMemoryNewsArticleRepository,
)


def _article(
    article_id: str,
    title: str,
    summary: str | None = None,
    symbols: tuple[str, ...] = (),
    sectors: tuple[str, ...] = (),
    published_at: datetime | None = None,
) -> NewsArticle:
    return NewsArticle(
        article_id=article_id,
        title=title,
        url=f"https://example.com/{article_id}",
        source="Example News",
        category=NewsCategory.COMPANY if symbols else NewsCategory.GLOBAL,
        published_at=published_at or datetime(2026, 7, 1, tzinfo=UTC),
        summary=summary,
        symbols=symbols,
        sectors=sectors,
    )


@pytest.mark.asyncio
async def test_rule_based_extractor_detects_earnings_beat_and_miss() -> None:
    extractor = RuleBasedEventExtractor()

    beat = await extractor.extract_events(
        _article(
            "a1",
            "Apple beats earnings estimates as revenue jumps",
            summary="Quarterly profit topped Wall Street expectations.",
            symbols=("AAPL",),
            sectors=("Technology",),
        )
    )
    miss = await extractor.extract_events(
        _article(
            "a2",
            "Acme misses earnings expectations as revenue falls short",
            summary="Quarterly results came in below estimates.",
            symbols=("ACME",),
        )
    )

    assert len(beat) == 1
    assert beat[0].event_type == EventType.EARNINGS_BEAT
    assert beat[0].sentiment == Sentiment.POSITIVE
    assert beat[0].importance == EventImportance.HIGH
    assert beat[0].symbols == ("AAPL",)
    assert beat[0].sectors == ("Technology",)
    assert 0.0 <= beat[0].confidence <= 1.0

    assert len(miss) == 1
    assert miss[0].event_type == EventType.EARNINGS_MISS
    assert miss[0].sentiment == Sentiment.NEGATIVE


@pytest.mark.asyncio
async def test_rule_based_extractor_ignores_non_events_and_false_earnings() -> None:
    extractor = RuleBasedEventExtractor()

    # "missed the deadline" must not be read as an earnings miss (no context).
    none_from_deadline = await extractor.extract_events(
        _article("a3", "Team missed the project deadline again")
    )
    # Generic filler with no financial event.
    none_from_filler = await extractor.extract_events(
        _article("a4", "A calm day in the markets with little to report")
    )

    assert none_from_deadline == []
    assert none_from_filler == []


@pytest.mark.asyncio
async def test_extraction_service_runs_pipeline_and_is_idempotent() -> None:
    article_repo = InMemoryNewsArticleRepository()
    await article_repo.upsert_articles(
        [
            _article(
                "a1",
                "Apple beats earnings estimates as revenue jumps",
                summary="Quarterly profit topped expectations.",
                symbols=("AAPL",),
                sectors=("Technology",),
            ),
            _article(
                "a2",
                "Regulator opens antitrust probe into big tech",
                summary="The watchdog launched an investigation.",
            ),
            _article(
                "a3",
                "A quiet session with nothing notable happening",
            ),
        ]
    )
    event_repo = InMemoryNewsEventRepository()
    service = EventExtractionService(
        article_repository=article_repo,
        event_repository=event_repo,
        extractor=RuleBasedEventExtractor(),
    )

    first = await service.extract_events(ExtractEventsRequest(limit=50))
    second = await service.extract_events(ExtractEventsRequest(limit=50))

    company_events = await service.list_events(
        EventQueryRequest(symbol="AAPL")
    )
    stats = await service.get_stats()

    # 3 articles processed, 2 yield events (one is a non-event), 1 stored per event.
    assert first.processed_count == 3
    assert first.extracted_count == 2
    assert first.stored_count == 2
    # Re-running is idempotent: the same deterministic event ids overwrite.
    assert stats.total_events == 2
    assert second.extracted_count == 2

    assert len(company_events.events) == 1
    assert company_events.events[0].event_type == EventType.EARNINGS_BEAT.value
    assert company_events.events[0].symbols == ("AAPL",)


@pytest.mark.asyncio
async def test_extraction_service_reports_when_no_extractor_configured() -> None:
    service = EventExtractionService(
        article_repository=InMemoryNewsArticleRepository(),
        event_repository=InMemoryNewsEventRepository(),
        extractor=None,
    )

    result = await service.extract_events(ExtractEventsRequest())

    assert result.stored_count == 0
    assert result.message == "No event extractor is configured."
