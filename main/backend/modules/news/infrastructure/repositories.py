from __future__ import annotations

import hashlib
from datetime import UTC
from datetime import date
from datetime import datetime
from datetime import timedelta
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.modules.market_data.infrastructure.clients import FinnhubClient
from backend.modules.news.application.providers import NewsProviderContract
from backend.modules.news.domain.entities import NewsArticle
from backend.modules.news.domain.entities import NewsCategory
from backend.modules.news.domain.repositories import NewsArticleRepository
from backend.modules.news.infrastructure.models import NewsArticleModel


class InMemoryNewsArticleRepository(NewsArticleRepository):
    def __init__(self) -> None:
        self._articles: dict[str, NewsArticle] = {}

    async def upsert_articles(
        self,
        articles: list[NewsArticle],
    ) -> int:
        for article in articles:
            existing_id = self._find_existing_id(article)
            self._articles[existing_id or article.article_id] = article
        return len(articles)

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
        articles = sorted(
            self._articles.values(),
            key=lambda article: article.published_at,
            reverse=True,
        )
        filtered = [
            article
            for article in articles
            if self._matches(article, category, symbol, sector, country, query)
        ]
        return filtered[offset : offset + limit]

    async def get_article(
        self,
        article_id: str,
    ) -> NewsArticle | None:
        return self._articles.get(article_id)

    async def get_stats(
        self,
    ) -> dict[str, int]:
        stats = {"total": len(self._articles)}
        for category in NewsCategory:
            stats[category.value] = len(
                [
                    article
                    for article in self._articles.values()
                    if article.category == category
                ]
            )
        return stats

    def _find_existing_id(
        self,
        article: NewsArticle,
    ) -> str | None:
        for existing in self._articles.values():
            if existing.url == article.url:
                return existing.article_id
            if article.content_hash and existing.content_hash == article.content_hash:
                return existing.article_id
        return None

    def _matches(
        self,
        article: NewsArticle,
        category: NewsCategory | None,
        symbol: str | None,
        sector: str | None,
        country: str | None,
        query: str | None,
    ) -> bool:
        if category is not None and article.category != category:
            return False
        if symbol is not None and symbol.upper() not in article.symbols:
            return False
        if sector is not None and sector.title() not in article.sectors:
            return False
        if country is not None and country.upper() not in article.countries:
            return False
        if query is not None:
            text = " ".join(
                value for value in (article.title, article.summary, article.body) if value
            ).lower()
            if query.lower() not in text:
                return False
        return True


class SqlNewsArticleRepository(NewsArticleRepository):
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def upsert_articles(
        self,
        articles: list[NewsArticle],
    ) -> int:
        for article in articles:
            stmt = select(NewsArticleModel).where(
                or_(
                    NewsArticleModel.article_id == article.article_id,
                    NewsArticleModel.url == article.url,
                    NewsArticleModel.content_hash == article.content_hash,
                )
            )
            result = await self._session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                self._session.add(self._entity_to_model(article))
                continue

            self._update_model(model, article)

        await self._session.flush()
        return len(articles)

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
        stmt = select(NewsArticleModel)
        if category is not None:
            stmt = stmt.where(NewsArticleModel.category == category.value)
        if query is not None:
            query_text = f"%{query}%"
            stmt = stmt.where(
                or_(
                    NewsArticleModel.title.ilike(query_text),
                    NewsArticleModel.summary.ilike(query_text),
                    NewsArticleModel.body.ilike(query_text),
                )
            )

        stmt = stmt.order_by(NewsArticleModel.published_at.desc())
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        articles = [self._model_to_entity(model) for model in models]
        filtered = [
            article
            for article in articles
            if self._matches_array_filters(article, symbol, sector, country)
        ]
        return filtered[offset : offset + limit]

    async def get_article(
        self,
        article_id: str,
    ) -> NewsArticle | None:
        stmt = select(NewsArticleModel).where(NewsArticleModel.article_id == article_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._model_to_entity(model)

    async def get_stats(
        self,
    ) -> dict[str, int]:
        total_result = await self._session.execute(
            select(func.count()).select_from(NewsArticleModel)
        )
        stats = {"total": int(total_result.scalar_one() or 0)}

        category_result = await self._session.execute(
            select(NewsArticleModel.category, func.count())
            .group_by(NewsArticleModel.category)
        )
        for category, count in category_result.all():
            stats[str(category)] = int(count)
        return stats

    def _matches_array_filters(
        self,
        article: NewsArticle,
        symbol: str | None,
        sector: str | None,
        country: str | None,
    ) -> bool:
        if symbol is not None and symbol.upper() not in article.symbols:
            return False
        if sector is not None and sector.title() not in article.sectors:
            return False
        if country is not None and country.upper() not in article.countries:
            return False
        return True

    def _entity_to_model(
        self,
        article: NewsArticle,
    ) -> NewsArticleModel:
        return NewsArticleModel(
            article_id=article.article_id,
            external_id=article.external_id,
            title=article.title,
            summary=article.summary,
            body=article.body,
            url=article.url,
            image_url=article.image_url,
            source=article.source,
            source_domain=article.source_domain,
            category=article.category.value,
            symbols=list(article.symbols),
            sectors=list(article.sectors),
            countries=list(article.countries),
            keywords=list(article.keywords),
            content_hash=article.content_hash,
            published_at=article.published_at,
            collected_at=article.collected_at,
        )

    def _update_model(
        self,
        model: NewsArticleModel,
        article: NewsArticle,
    ) -> None:
        model.external_id = article.external_id
        model.title = article.title
        model.summary = article.summary
        model.body = article.body
        model.url = article.url
        model.image_url = article.image_url
        model.source = article.source
        model.source_domain = article.source_domain
        model.category = article.category.value
        model.symbols = list(article.symbols)
        model.sectors = list(article.sectors)
        model.countries = list(article.countries)
        model.keywords = list(article.keywords)
        model.content_hash = article.content_hash
        model.published_at = article.published_at
        model.collected_at = article.collected_at

    def _model_to_entity(
        self,
        model: NewsArticleModel,
    ) -> NewsArticle:
        return NewsArticle(
            article_id=model.article_id,
            external_id=model.external_id,
            title=model.title,
            summary=model.summary,
            body=model.body,
            url=model.url,
            image_url=model.image_url,
            source=model.source,
            source_domain=model.source_domain,
            category=NewsCategory(model.category),
            symbols=tuple(model.symbols or ()),
            sectors=tuple(model.sectors or ()),
            countries=tuple(model.countries or ()),
            keywords=tuple(model.keywords or ()),
            content_hash=model.content_hash,
            published_at=self._ensure_aware(model.published_at),
            collected_at=self._ensure_aware(model.collected_at),
        )

    def _ensure_aware(
        self,
        value: datetime,
    ) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class FinnhubNewsProvider(NewsProviderContract):
    def __init__(
        self,
        client: FinnhubClient,
    ) -> None:
        self._client = client

    async def collect_news(
        self,
        category: NewsCategory,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        symbols: tuple[str, ...] = (),
        sectors: tuple[str, ...] = (),
        limit: int = 50,
    ) -> list[NewsArticle]:
        if category == NewsCategory.COMPANY:
            return await self._collect_company_news(symbols, start_at, end_at, limit)

        payload = await self._client.get_market_news("general")
        articles = [
            self._from_finnhub_item(item, category=category)
            for item in payload
            if self._has_required_fields(item)
        ]
        articles = self._filter_dates(articles, start_at, end_at)

        if category == NewsCategory.INDIA:
            articles = [article for article in articles if self._mentions_india(article)]
        elif category == NewsCategory.SECTOR and sectors:
            articles = [
                article
                for article in articles
                if self._mentions_any_sector(article, sectors)
            ]

        return articles[:limit]

    async def _collect_company_news(
        self,
        symbols: tuple[str, ...],
        start_at: datetime | None,
        end_at: datetime | None,
        limit: int,
    ) -> list[NewsArticle]:
        if not symbols:
            return []

        end_date = (end_at or datetime.now(UTC)).date()
        start_date = (start_at.date() if start_at is not None else end_date - timedelta(days=7))
        articles: list[NewsArticle] = []

        for symbol in symbols:
            payload = await self._client.get_company_news(
                symbol=symbol,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
            for item in payload:
                if not self._has_required_fields(item):
                    continue
                article = self._from_finnhub_item(
                    item,
                    category=NewsCategory.COMPANY,
                    symbols=(symbol,),
                )
                articles.append(article)

        return self._filter_dates(articles, start_at, end_at)[:limit]

    def _from_finnhub_item(
        self,
        item: dict[str, Any],
        category: NewsCategory,
        symbols: tuple[str, ...] = (),
    ) -> NewsArticle:
        title = str(item.get("headline") or item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        summary = self._optional_text(item.get("summary"))
        source = str(item.get("source") or "Finnhub").strip()
        external_id = self._optional_text(item.get("id"))
        published_at = self._timestamp(item.get("datetime"))
        content_hash = self._content_hash(title, summary, url)
        related = self._optional_text(item.get("related"))
        article_symbols = symbols or self._split_related_symbols(related)

        return NewsArticle(
            article_id=content_hash,
            external_id=external_id,
            title=title,
            summary=summary,
            url=url,
            image_url=self._optional_text(item.get("image")),
            source=source,
            source_domain=urlparse(url).netloc.lower() or None,
            category=category,
            symbols=tuple(symbol.upper() for symbol in article_symbols),
            content_hash=content_hash,
            published_at=published_at,
            collected_at=datetime.now(UTC),
        )

    def _has_required_fields(
        self,
        item: dict[str, Any],
    ) -> bool:
        return bool(item.get("url")) and bool(item.get("headline") or item.get("title"))

    def _filter_dates(
        self,
        articles: list[NewsArticle],
        start_at: datetime | None,
        end_at: datetime | None,
    ) -> list[NewsArticle]:
        if start_at is not None:
            articles = [article for article in articles if article.published_at >= start_at]
        if end_at is not None:
            articles = [article for article in articles if article.published_at <= end_at]
        return articles

    def _mentions_india(
        self,
        article: NewsArticle,
    ) -> bool:
        text = f" {article.title} {article.summary or ''} ".lower()
        return any(
            token in text
            for token in (" india ", " indian ", " nse ", " bse ", " nifty", " sensex", " rbi ")
        )

    def _mentions_any_sector(
        self,
        article: NewsArticle,
        sectors: tuple[str, ...],
    ) -> bool:
        text = f" {article.title} {article.summary or ''} ".lower()
        return any(sector.lower() in text for sector in sectors)

    def _optional_text(
        self,
        raw_value: Any,
    ) -> str | None:
        if raw_value in (None, ""):
            return None
        return str(raw_value)

    def _timestamp(
        self,
        raw_value: Any,
    ) -> datetime:
        if raw_value in (None, "", 0, "0"):
            return datetime.now(UTC)
        if isinstance(raw_value, datetime):
            return raw_value if raw_value.tzinfo else raw_value.replace(tzinfo=UTC)
        if isinstance(raw_value, date):
            return datetime.combine(raw_value, datetime.min.time(), tzinfo=UTC)
        return datetime.fromtimestamp(int(raw_value), tz=UTC)

    def _split_related_symbols(
        self,
        related: str | None,
    ) -> tuple[str, ...]:
        if not related:
            return ()
        return tuple(
            symbol.strip().upper()
            for symbol in related.split(",")
            if symbol.strip()
        )

    def _content_hash(
        self,
        title: str,
        summary: str | None,
        url: str,
    ) -> str:
        fingerprint = "|".join((title.lower(), (summary or "").lower(), url.lower()))
        return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
