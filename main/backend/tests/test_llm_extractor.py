from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.modules.events.domain.entities import EventType, Sentiment
from backend.modules.events.infrastructure.extractors import RuleBasedEventExtractor
from backend.modules.events.infrastructure.llm_extractor import LLMEventExtractor
from backend.modules.news.domain.entities import NewsArticle, NewsCategory
from backend.shared.llm import LLMClient, extract_json_object


class FakeLLM(LLMClient):
    """Returns a canned response (or raises) so the adapter is tested offline."""

    def __init__(self, response: str | None = None, error: Exception | None = None) -> None:
        self._response = response
        self._error = error

    async def complete(self, system, user, temperature=0.0, max_tokens=None) -> str:
        if self._error is not None:
            raise self._error
        return self._response or ""


def _article() -> NewsArticle:
    return NewsArticle(
        article_id="a1",
        title="NVIDIA beats earnings estimates as data-center revenue surges",
        url="https://example.com/a1",
        source="Example News",
        category=NewsCategory.COMPANY,
        published_at=datetime(2026, 7, 1, tzinfo=UTC),
        summary="Quarterly profit topped expectations.",
        symbols=("NVDA",),
        sectors=("Technology",),
    )


def test_extract_json_object_handles_fenced_and_noisy_text() -> None:
    assert extract_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json_object('Sure! Here it is: {"b": 2} hope that helps') == {"b": 2}
    with pytest.raises(ValueError):
        extract_json_object("no json here")


@pytest.mark.asyncio
async def test_llm_extractor_maps_json_to_event() -> None:
    llm = FakeLLM(
        response=(
            '{"is_event": true, "event_type": "earnings_beat", '
            '"sentiment": "positive", "importance": "high", '
            '"confidence": 0.9, "summary": "NVIDIA beat estimates."}'
        )
    )
    extractor = LLMEventExtractor(llm)

    events = await extractor.extract_events(_article())

    assert len(events) == 1
    event = events[0]
    assert event.event_type == EventType.EARNINGS_BEAT
    assert event.sentiment == Sentiment.POSITIVE
    assert event.symbols == ("NVDA",)
    assert event.source == "llm"
    assert 0.0 <= event.confidence <= 1.0


@pytest.mark.asyncio
async def test_llm_extractor_returns_empty_when_not_an_event() -> None:
    llm = FakeLLM(response='{"is_event": false}')
    extractor = LLMEventExtractor(llm)
    assert await extractor.extract_events(_article()) == []


@pytest.mark.asyncio
async def test_llm_extractor_falls_back_on_error() -> None:
    # When the LLM call fails, the rule-based fallback still finds the beat.
    llm = FakeLLM(error=RuntimeError("connection refused"))
    extractor = LLMEventExtractor(llm, fallback=RuleBasedEventExtractor())

    events = await extractor.extract_events(_article())

    assert len(events) == 1
    assert events[0].event_type == EventType.EARNINGS_BEAT
    assert events[0].source == "rule-based"


@pytest.mark.asyncio
async def test_llm_extractor_no_fallback_on_error_returns_empty() -> None:
    llm = FakeLLM(error=RuntimeError("boom"))
    extractor = LLMEventExtractor(llm, fallback=None)
    assert await extractor.extract_events(_article()) == []
