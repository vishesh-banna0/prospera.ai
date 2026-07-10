from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from datetime import datetime

from backend.modules.news.domain.entities import NewsArticle
from backend.modules.news.domain.entities import NewsCategory


class NewsProviderContract(ABC):
    @abstractmethod
    async def collect_news(
        self,
        category: NewsCategory,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        symbols: tuple[str, ...] = (),
        sectors: tuple[str, ...] = (),
        limit: int = 50,
    ) -> list[NewsArticle]:
        raise NotImplementedError
