from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SyncNewsRequest:
    categories: tuple[str, ...] = ("global", "india", "company", "sector")
    symbols: tuple[str, ...] = ()
    sectors: tuple[str, ...] = ()
    start_at: datetime | None = None
    end_at: datetime | None = None
    limit: int = 50


@dataclass(frozen=True, slots=True)
class NewsQueryRequest:
    category: str | None = None
    symbol: str | None = None
    sector: str | None = None
    country: str | None = None
    query: str | None = None
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True, slots=True)
class NewsArticleView:
    article_id: str
    title: str
    url: str
    source: str
    category: str
    published_at: datetime
    summary: str | None = None
    body: str | None = None
    external_id: str | None = None
    image_url: str | None = None
    source_domain: str | None = None
    symbols: tuple[str, ...] = field(default_factory=tuple)
    sectors: tuple[str, ...] = field(default_factory=tuple)
    countries: tuple[str, ...] = field(default_factory=tuple)
    keywords: tuple[str, ...] = field(default_factory=tuple)
    content_hash: str | None = None
    collected_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class NewsArticlesView:
    articles: tuple[NewsArticleView, ...]
    count: int
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class SyncNewsView:
    requested_categories: tuple[str, ...]
    fetched_count: int
    stored_count: int
    duplicate_count: int
    message: str | None = None


@dataclass(frozen=True, slots=True)
class NewsWarehouseStatsView:
    total_articles: int
    global_articles: int
    india_articles: int
    company_articles: int
    sector_articles: int
