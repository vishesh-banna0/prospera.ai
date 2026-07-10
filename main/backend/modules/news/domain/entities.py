from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC
from datetime import datetime
from enum import StrEnum


class NewsCategory(StrEnum):
    GLOBAL = "global"
    INDIA = "india"
    COMPANY = "company"
    SECTOR = "sector"


@dataclass(frozen=True, slots=True)
class NewsArticle:
    article_id: str
    title: str
    url: str
    source: str
    category: NewsCategory
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
    collected_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("News article title cannot be blank.")
        if not self.url.strip():
            raise ValueError("News article URL cannot be blank.")
        if self.published_at.tzinfo is None:
            raise ValueError("News article published_at must be timezone aware.")
