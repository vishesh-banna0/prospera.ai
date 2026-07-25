from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC
from datetime import datetime
from enum import StrEnum


class EventType(StrEnum):
    """The kind of financial event described by a news article.

    Kept intentionally broad so the enum is stable as extractors improve.
    The Phase 8 rule-based extractor only detects a useful subset reliably;
    a future LLM-based extractor can populate the rest without a schema change.
    """

    EARNINGS_BEAT = "earnings_beat"
    EARNINGS_MISS = "earnings_miss"
    EARNINGS = "earnings"
    GUIDANCE_RAISED = "guidance_raised"
    GUIDANCE_CUT = "guidance_cut"
    MERGER_ACQUISITION = "merger_acquisition"
    IPO = "ipo"
    DIVIDEND = "dividend"
    LEADERSHIP_CHANGE = "leadership_change"
    REGULATORY = "regulatory"
    LEGAL = "legal"
    LAYOFFS = "layoffs"
    ANALYST_RATING = "analyst_rating"
    PARTNERSHIP = "partnership"
    PRODUCT_LAUNCH = "product_launch"

    # Macro / market-wide events (not tied to a single company). These are
    # articles about the broader environment stocks trade in: cross-border
    # conflict, central-bank policy, trade measures, economic data releases, and
    # sector-wide moves.
    GEOPOLITICAL = "geopolitical"
    MONETARY_POLICY = "monetary_policy"
    TRADE_POLICY = "trade_policy"
    MACRO_INDICATOR = "macro_indicator"
    SECTOR_TREND = "sector_trend"

    OTHER = "other"


class Sentiment(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class EventImportance(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True, slots=True)
class NewsEvent:
    """A structured event extracted from one news article.

    This is the core Phase 8 output: the bridge between free-text news and
    every downstream numeric/reasoning phase. It intentionally snapshots the
    article's headline, symbols, sectors, and date so an event is
    self-contained and can be reasoned about without re-reading the article.
    """

    event_id: str
    article_id: str

    event_type: EventType
    sentiment: Sentiment
    importance: EventImportance

    headline: str
    event_date: datetime

    summary: str | None = None
    symbols: tuple[str, ...] = field(default_factory=tuple)
    sectors: tuple[str, ...] = field(default_factory=tuple)
    keywords: tuple[str, ...] = field(default_factory=tuple)

    confidence: float = 0.5
    source: str = "rule-based"

    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.event_id.strip():
            raise ValueError("News event id cannot be blank.")
        if not self.article_id.strip():
            raise ValueError("News event article_id cannot be blank.")
        if not self.headline.strip():
            raise ValueError("News event headline cannot be blank.")
        if self.event_date.tzinfo is None:
            raise ValueError("News event event_date must be timezone aware.")

        clamped_confidence = min(1.0, max(0.0, float(self.confidence)))
        object.__setattr__(self, "confidence", clamped_confidence)


# Purpose:
# Defines the structured event vocabulary produced by the Phase 8 engine.
#
# Responsibilities:
# - Describe event type, sentiment, and importance as closed enums.
# - Represent one extracted event as an immutable, self-contained record.
# - Protect invariants (non-blank ids/headline, tz-aware date, bounded confidence).
#
# Dependencies:
# - None outside the standard library.
#
# What Should Not Live Here:
# - Extraction logic (belongs in an extractor adapter).
# - ORM mappings or SQL.
# - HTTP/serialization concerns.
