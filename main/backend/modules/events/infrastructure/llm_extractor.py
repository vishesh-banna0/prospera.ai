from __future__ import annotations

import hashlib
import logging

from backend.modules.events.application.extractors import EventExtractorContract
from backend.modules.events.domain.entities import (
    EventImportance,
    EventType,
    NewsEvent,
    Sentiment,
)
from backend.modules.news.domain.entities import NewsArticle
from backend.shared.llm import LLMClient, extract_json_object

logger = logging.getLogger(__name__)


_SYSTEM_PROMPT = (
    "You are a financial news analyst. Given one news article, decide whether it "
    "describes a concrete, market-relevant financial event. Respond with ONLY a "
    "JSON object and no other text, using exactly these keys:\n"
    '{"is_event": true|false, "event_type": <one of the allowed types>, '
    '"sentiment": "positive"|"negative"|"neutral", '
    '"importance": "high"|"medium"|"low", "confidence": <0..1>, '
    '"summary": <one short sentence>}\n'
    "Allowed event_type values: "
    "earnings_beat, earnings_miss, earnings, guidance_raised, guidance_cut, "
    "merger_acquisition, ipo, dividend, leadership_change, regulatory, legal, "
    "layoffs, analyst_rating, partnership, product_launch, geopolitical, "
    "monetary_policy, trade_policy, macro_indicator, sector_trend, other.\n"
    "Use geopolitical for cross-border conflict/war, monetary_policy for "
    "central-bank rate decisions, trade_policy for tariffs/trade measures, "
    "macro_indicator for economic data (inflation, GDP, jobs), and sector_trend "
    "for sector-wide moves. If the article is not about a specific financial "
    "event, set is_event to false."
)


class LLMEventExtractor(EventExtractorContract):
    """LLM-backed event extractor (same contract as the rule-based default).

    Prompts a locally-hosted, OpenAI-compatible chat model (e.g. Ollama Llama)
    for a structured JSON classification of one article, then maps it onto the
    ``NewsEvent`` schema. It reuses the deterministic ``event_id`` scheme so
    re-running extraction stays idempotent regardless of which extractor ran.

    Robustness first: any failure (network down, bad JSON, unknown enum value)
    falls back to the injected rule-based extractor (or an empty result), so
    enabling the LLM never makes the pipeline less reliable than the default.
    """

    source = "llm"

    def __init__(
        self,
        llm: LLMClient,
        fallback: EventExtractorContract | None = None,
    ) -> None:
        self._llm = llm
        self._fallback = fallback

    async def extract_events(self, article: NewsArticle) -> list[NewsEvent]:
        text = self._build_text(article)
        if not text:
            return []

        try:
            raw = await self._llm.complete(system=_SYSTEM_PROMPT, user=text)
            parsed = extract_json_object(raw)
        except Exception as exc:
            logger.warning("LLM extraction failed (%s); using fallback.", exc)
            return await self._fallback_extract(article)

        if not bool(parsed.get("is_event")):
            return []

        event_type = self._coerce_event_type(parsed.get("event_type"))
        sentiment = self._coerce_enum(parsed.get("sentiment"), Sentiment, Sentiment.NEUTRAL)
        importance = self._coerce_enum(
            parsed.get("importance"), EventImportance, EventImportance.MEDIUM
        )
        primary_symbol = article.symbols[0] if article.symbols else ""

        event = NewsEvent(
            event_id=self._event_id(article.article_id, event_type, primary_symbol),
            article_id=article.article_id,
            event_type=event_type,
            sentiment=sentiment,
            importance=importance,
            headline=article.title,
            summary=self._coerce_summary(parsed.get("summary"), article.summary),
            symbols=article.symbols,
            sectors=article.sectors,
            keywords=article.keywords,
            confidence=self._coerce_confidence(parsed.get("confidence")),
            source=self.source,
            event_date=article.published_at,
        )
        return [event]

    async def _fallback_extract(self, article: NewsArticle) -> list[NewsEvent]:
        if self._fallback is None:
            return []
        return await self._fallback.extract_events(article)

    def _build_text(self, article: NewsArticle) -> str:
        parts = [article.title, article.summary or "", article.body or ""]
        return "\n".join(part for part in parts if part).strip()

    def _coerce_event_type(self, raw: object) -> EventType:
        try:
            return EventType(str(raw).strip().lower())
        except ValueError:
            return EventType.OTHER

    def _coerce_enum(self, raw: object, enum_cls, default):
        try:
            return enum_cls(str(raw).strip().lower())
        except ValueError:
            return default

    def _coerce_confidence(self, raw: object) -> float:
        try:
            return min(1.0, max(0.0, float(raw)))
        except (TypeError, ValueError):
            return 0.6

    def _coerce_summary(self, raw: object, default: str | None) -> str | None:
        if raw in (None, ""):
            return default
        return str(raw).strip() or default

    def _event_id(
        self,
        article_id: str,
        event_type: EventType,
        primary_symbol: str,
    ) -> str:
        fingerprint = "|".join((article_id, event_type.value, primary_symbol))
        return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
