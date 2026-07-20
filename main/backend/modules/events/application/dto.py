from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


# ============================================================
# Inputs
# ============================================================


@dataclass(frozen=True, slots=True)
class ExtractEventsRequest:
    """Selects which warehouse articles to run extraction over.

    If ``article_ids`` is provided, only those articles are processed.
    Otherwise the warehouse is queried using the optional filters below.
    """

    article_ids: tuple[str, ...] = ()
    category: str | None = None
    symbol: str | None = None
    sector: str | None = None
    query: str | None = None
    limit: int = 50


@dataclass(frozen=True, slots=True)
class EventQueryRequest:
    event_type: str | None = None
    symbol: str | None = None
    sector: str | None = None
    sentiment: str | None = None
    importance: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    limit: int = 50
    offset: int = 0


# ============================================================
# Views
# ============================================================


@dataclass(frozen=True, slots=True)
class EventView:
    event_id: str
    article_id: str
    event_type: str
    sentiment: str
    importance: str
    headline: str
    event_date: datetime
    summary: str | None = None
    symbols: tuple[str, ...] = field(default_factory=tuple)
    sectors: tuple[str, ...] = field(default_factory=tuple)
    keywords: tuple[str, ...] = field(default_factory=tuple)
    confidence: float = 0.5
    source: str = "rule-based"
    created_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class EventsView:
    events: tuple[EventView, ...]
    count: int
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class ExtractEventsView:
    processed_count: int
    extracted_count: int
    stored_count: int
    message: str | None = None


@dataclass(frozen=True, slots=True)
class EventTypeCount:
    event_type: str
    count: int


@dataclass(frozen=True, slots=True)
class EventStatsView:
    total_events: int
    by_type: tuple[EventTypeCount, ...]
