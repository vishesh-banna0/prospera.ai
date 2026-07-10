from __future__ import annotations

import hashlib
import re
from dataclasses import replace
from datetime import UTC
from datetime import datetime
from typing import Iterable
from urllib.parse import urlparse

from backend.modules.news.application.dto import (
    NewsArticleView,
    NewsArticlesView,
    NewsQueryRequest,
    NewsWarehouseStatsView,
    SyncNewsRequest,
    SyncNewsView,
)
from backend.modules.news.application.providers import NewsProviderContract
from backend.modules.news.domain.entities import NewsArticle
from backend.modules.news.domain.entities import NewsCategory
from backend.modules.news.domain.repositories import NewsArticleRepository


class NewsIntelligenceService:
    def __init__(
        self,
        repository: NewsArticleRepository,
        provider: NewsProviderContract | None = None,
        commit=None,
    ) -> None:
        self._repository = repository
        self._provider = provider
        self._commit = commit

    async def sync_news(
        self,
        request: SyncNewsRequest,
    ) -> SyncNewsView:
        categories = self._normalize_categories(request.categories)
        symbols = self._normalize_labels(request.symbols, uppercase=True)
        sectors = self._normalize_labels(request.sectors)
        limit = self._normalize_limit(request.limit)
        start_at = self._normalize_datetime(request.start_at)
        end_at = self._normalize_datetime(request.end_at)

        if self._provider is None:
            return SyncNewsView(
                requested_categories=tuple(category.value for category in categories),
                fetched_count=0,
                stored_count=0,
                duplicate_count=0,
                message="No news provider is configured.",
            )

        collected: list[NewsArticle] = []
        for category in categories:
            collected.extend(
                await self._provider.collect_news(
                    category=category,
                    start_at=start_at,
                    end_at=end_at,
                    symbols=symbols,
                    sectors=sectors,
                    limit=limit,
                )
            )

        cleaned = [self._classify_article(self._clean_article(article)) for article in collected]
        deduplicated = self._deduplicate(cleaned)
        stored_count = await self._repository.upsert_articles(deduplicated)

        if self._commit is not None:
            await self._commit()

        return SyncNewsView(
            requested_categories=tuple(category.value for category in categories),
            fetched_count=len(collected),
            stored_count=stored_count,
            duplicate_count=max(0, len(collected) - len(deduplicated)),
        )

    async def list_articles(
        self,
        request: NewsQueryRequest,
    ) -> NewsArticlesView:
        category = self._optional_category(request.category)
        limit = self._normalize_limit(request.limit)
        offset = max(0, request.offset)

        articles = await self._repository.list_articles(
            category=category,
            symbol=self._optional_upper(request.symbol),
            sector=self._optional_text(request.sector),
            country=self._optional_upper(request.country),
            query=self._optional_text(request.query),
            limit=limit,
            offset=offset,
        )

        return NewsArticlesView(
            articles=tuple(self._to_view(article) for article in articles),
            count=len(articles),
            limit=limit,
            offset=offset,
        )

    async def get_article(
        self,
        article_id: str,
    ) -> NewsArticleView:
        article = await self._repository.get_article(article_id)
        if article is None:
            raise ValueError(f"News article '{article_id}' was not found.")
        return self._to_view(article)

    async def get_warehouse_stats(
        self,
    ) -> NewsWarehouseStatsView:
        stats = await self._repository.get_stats()
        return NewsWarehouseStatsView(
            total_articles=stats.get("total", 0),
            global_articles=stats.get(NewsCategory.GLOBAL.value, 0),
            india_articles=stats.get(NewsCategory.INDIA.value, 0),
            company_articles=stats.get(NewsCategory.COMPANY.value, 0),
            sector_articles=stats.get(NewsCategory.SECTOR.value, 0),
        )

    def _clean_article(
        self,
        article: NewsArticle,
    ) -> NewsArticle:
        title = self._collapse_whitespace(article.title)
        summary = self._optional_clean(article.summary)
        body = self._optional_clean(article.body)
        url = article.url.strip()
        source = self._collapse_whitespace(article.source) or "unknown"
        source_domain = article.source_domain or self._domain_from_url(url)
        content_hash = article.content_hash or self._content_hash(title, summary, url)
        article_id = article.article_id or content_hash

        return replace(
            article,
            article_id=article_id,
            title=title,
            summary=summary,
            body=body,
            url=url,
            source=source,
            source_domain=source_domain,
            content_hash=content_hash,
            symbols=self._normalize_labels(article.symbols, uppercase=True),
            sectors=self._normalize_labels(article.sectors),
            countries=self._normalize_labels(article.countries, uppercase=True),
            keywords=self._normalize_labels(article.keywords),
        )

    def _classify_article(
        self,
        article: NewsArticle,
    ) -> NewsArticle:
        text = " ".join(
            value for value in (article.title, article.summary, article.body) if value
        ).lower()
        countries = set(article.countries)
        sectors = set(article.sectors)
        symbols = set(article.symbols)
        keywords = set(article.keywords)
        category = article.category

        if self._mentions_india(text):
            countries.add("IN")
            if category == NewsCategory.GLOBAL:
                category = NewsCategory.INDIA

        matched_sectors = self._match_sectors(text)
        if matched_sectors:
            sectors.update(matched_sectors)
            if category == NewsCategory.GLOBAL:
                category = NewsCategory.SECTOR
        elif category == NewsCategory.SECTOR and not sectors:
            category = NewsCategory.GLOBAL

        if symbols:
            category = NewsCategory.COMPANY

        keywords.update(self._extract_keywords(text))

        return replace(
            article,
            category=category,
            countries=tuple(sorted(countries)),
            sectors=tuple(sorted(sectors)),
            symbols=tuple(sorted(symbols)),
            keywords=tuple(sorted(keywords)),
        )

    def _deduplicate(
        self,
        articles: Iterable[NewsArticle],
    ) -> list[NewsArticle]:
        seen: set[str] = set()
        unique: list[NewsArticle] = []
        for article in articles:
            keys = {
                article.url.lower(),
                article.content_hash or "",
                article.external_id or "",
            }
            keys.discard("")
            if seen.intersection(keys):
                continue
            seen.update(keys)
            unique.append(article)
        return unique

    def _normalize_categories(
        self,
        categories: tuple[str, ...],
    ) -> tuple[NewsCategory, ...]:
        raw_categories = categories or tuple(category.value for category in NewsCategory)
        normalized: list[NewsCategory] = []
        for raw_category in raw_categories:
            category = NewsCategory(str(raw_category).strip().lower())
            if category not in normalized:
                normalized.append(category)
        return tuple(normalized)

    def _optional_category(
        self,
        raw_category: str | None,
    ) -> NewsCategory | None:
        if raw_category is None or not str(raw_category).strip():
            return None
        return NewsCategory(str(raw_category).strip().lower())

    def _normalize_limit(
        self,
        limit: int,
    ) -> int:
        return min(max(1, int(limit)), 200)

    def _normalize_datetime(
        self,
        value: datetime | None,
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

    def _normalize_labels(
        self,
        labels: tuple[str, ...],
        uppercase: bool = False,
    ) -> tuple[str, ...]:
        values = []
        for label in labels:
            clean = self._collapse_whitespace(str(label))
            if not clean:
                continue
            values.append(clean.upper() if uppercase else clean.title())
        return tuple(sorted(set(values)))

    def _optional_text(
        self,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None
        clean = self._collapse_whitespace(value)
        return clean or None

    def _optional_upper(
        self,
        value: str | None,
    ) -> str | None:
        clean = self._optional_text(value)
        return clean.upper() if clean is not None else None

    def _collapse_whitespace(
        self,
        value: str,
    ) -> str:
        return re.sub(r"\s+", " ", value).strip()

    def _optional_clean(
        self,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None
        clean = self._collapse_whitespace(value)
        return clean or None

    def _content_hash(
        self,
        title: str,
        summary: str | None,
        url: str,
    ) -> str:
        fingerprint = "|".join((title.lower(), (summary or "").lower(), url.lower()))
        return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()

    def _domain_from_url(
        self,
        url: str,
    ) -> str | None:
        domain = urlparse(url).netloc.lower()
        return domain or None

    def _mentions_india(
        self,
        text: str,
    ) -> bool:
        text = f" {text} "
        return any(
            token in text
            for token in (
                " india ",
                " indian ",
                " nse ",
                " bse ",
                " sensex",
                " nifty",
                " rbi ",
                " rupee",
                " mumbai",
            )
        )

    def _match_sectors(
        self,
        text: str,
    ) -> tuple[str, ...]:
        sector_keywords = {
            "Technology": ("technology", "software", "semiconductor", "ai ", "cloud"),
            "Financial Services": ("bank", "lender", "insurance", "fintech", "nbfc"),
            "Energy": ("energy", "oil", "gas", "renewable", "power"),
            "Healthcare": ("healthcare", "pharma", "biotech", "hospital"),
            "Consumer": ("consumer", "retail", "fmcg", "e-commerce"),
            "Industrials": ("manufacturing", "industrial", "infrastructure", "cement"),
        }
        matches = [
            sector
            for sector, keywords in sector_keywords.items()
            if any(keyword in text for keyword in keywords)
        ]
        return tuple(matches)

    def _extract_keywords(
        self,
        text: str,
    ) -> tuple[str, ...]:
        watched_terms = (
            "earnings",
            "inflation",
            "rates",
            "merger",
            "acquisition",
            "ipo",
            "guidance",
            "revenue",
            "profit",
            "policy",
        )
        return tuple(term for term in watched_terms if term in text)

    def _to_view(
        self,
        article: NewsArticle,
    ) -> NewsArticleView:
        return NewsArticleView(
            article_id=article.article_id,
            title=article.title,
            url=article.url,
            source=article.source,
            category=article.category.value,
            published_at=article.published_at,
            summary=article.summary,
            body=article.body,
            external_id=article.external_id,
            image_url=article.image_url,
            source_domain=article.source_domain,
            symbols=article.symbols,
            sectors=article.sectors,
            countries=article.countries,
            keywords=article.keywords,
            content_hash=article.content_hash,
            collected_at=article.collected_at,
        )
