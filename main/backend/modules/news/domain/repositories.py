from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from backend.modules.news.domain.entities import NewsArticle
from backend.modules.news.domain.entities import NewsCategory


class NewsArticleRepository(ABC):
    @abstractmethod
    async def upsert_articles(
        self,
        articles: list[NewsArticle],
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    async def list_articles(
        self,
        category: NewsCategory | None = None,
        symbol: str | None = None,
        sector: str | None = None,
        country: str | None = None,
        query: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[NewsArticle]:
        raise NotImplementedError

    @abstractmethod
    async def get_article(
        self,
        article_id: str,
    ) -> NewsArticle | None:
        raise NotImplementedError

    @abstractmethod
    async def get_stats(
        self,
    ) -> dict[str, int]:
        raise NotImplementedError
