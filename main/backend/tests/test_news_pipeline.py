from __future__ import annotations

from datetime import UTC
from datetime import datetime

import httpx
import pytest

from backend.modules.market_data.infrastructure.clients import FinnhubClient
from backend.modules.news.application.dto import NewsQueryRequest
from backend.modules.news.application.dto import SyncNewsRequest
from backend.modules.news.application.services import NewsIntelligenceService
from backend.modules.news.domain.entities import NewsArticle
from backend.modules.news.domain.entities import NewsCategory
from backend.modules.news.infrastructure.repositories import FinnhubNewsProvider
from backend.modules.news.infrastructure.repositories import InMemoryNewsArticleRepository


class StubSettings:
    market_data_provider = "finnhub"
    market_data_api_key = "test-key"
    market_data_base_url = "https://finnhub.io/api/v1"


class StubNewsProvider:
    async def collect_news(
        self,
        category: NewsCategory,
        start_at=None,
        end_at=None,
        symbols: tuple[str, ...] = (),
        sectors: tuple[str, ...] = (),
        limit: int = 50,
    ) -> list[NewsArticle]:
        if category == NewsCategory.COMPANY:
            return [
                NewsArticle(
                    article_id="",
                    title=" Apple posts earnings beat ",
                    url="https://example.com/apple-earnings",
                    source=" Example News ",
                    category=category,
                    published_at=datetime(2026, 7, 1, tzinfo=UTC),
                    summary=" Revenue and profit climbed. ",
                    symbols=symbols,
                )
            ]

        return [
            NewsArticle(
                article_id="",
                title="India technology stocks rally on policy support",
                url="https://example.com/india-tech",
                source="Example News",
                category=category,
                published_at=datetime(2026, 7, 2, tzinfo=UTC),
                summary="Nifty software companies gained after new policy details.",
            ),
            NewsArticle(
                article_id="duplicate",
                title="India technology stocks rally on policy support",
                url="https://example.com/india-tech",
                source="Example News",
                category=category,
                published_at=datetime(2026, 7, 2, tzinfo=UTC),
                summary="Nifty software companies gained after new policy details.",
            ),
        ]


@pytest.mark.asyncio
async def test_news_service_syncs_cleans_classifies_and_deduplicates() -> None:
    service = NewsIntelligenceService(
        repository=InMemoryNewsArticleRepository(),
        provider=StubNewsProvider(),
    )

    result = await service.sync_news(
        SyncNewsRequest(
            categories=("global", "company"),
            symbols=("aapl",),
        )
    )
    india_articles = await service.list_articles(
        NewsQueryRequest(category="india", country="IN")
    )
    company_articles = await service.list_articles(
        NewsQueryRequest(category="company", symbol="AAPL")
    )
    stats = await service.get_warehouse_stats()

    assert result.fetched_count == 3
    assert result.stored_count == 2
    assert result.duplicate_count == 1
    assert len(india_articles.articles) == 1
    assert india_articles.articles[0].countries == ("IN",)
    assert "Technology" in india_articles.articles[0].sectors
    assert len(company_articles.articles) == 1
    assert company_articles.articles[0].title == "Apple posts earnings beat"
    assert company_articles.articles[0].symbols == ("AAPL",)
    assert stats.total_articles == 2


def _build_mock_client() -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        params = dict(request.url.params)

        if params.get("token") != "test-key":
            return httpx.Response(401, json={"error": "Invalid API key"})

        if path.endswith("/news"):
            return httpx.Response(
                200,
                json=[
                    {
                        "category": "general",
                        "datetime": 1782950400,
                        "headline": "India banks rise as Nifty hits record",
                        "id": 1001,
                        "image": "https://example.com/image.jpg",
                        "source": "Wire",
                        "summary": "Indian lenders gained in Mumbai trade.",
                        "url": "https://example.com/india-banks",
                    }
                ],
            )

        if path.endswith("/company-news") and params.get("symbol") == "AAPL":
            return httpx.Response(
                200,
                json=[
                    {
                        "datetime": 1782864000,
                        "headline": "Apple unveils new cloud service",
                        "id": 2001,
                        "image": "",
                        "related": "AAPL",
                        "source": "Wire",
                        "summary": "The company expanded its software lineup.",
                        "url": "https://example.com/apple-cloud",
                    }
                ],
            )

        return httpx.Response(404, json={"error": f"Unhandled path: {path}"})

    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(
        transport=transport,
        base_url="https://finnhub.io/api/v1",
    )


@pytest.mark.asyncio
async def test_finnhub_news_provider_normalizes_general_and_company_news() -> None:
    async with _build_mock_client() as http_client:
        provider = FinnhubNewsProvider(
            FinnhubClient(
                settings=StubSettings(),
                http_client=http_client,
            )
        )

        india_articles = await provider.collect_news(NewsCategory.INDIA)
        company_articles = await provider.collect_news(
            NewsCategory.COMPANY,
            symbols=("AAPL",),
        )

    assert len(india_articles) == 1
    assert india_articles[0].category == NewsCategory.INDIA
    assert india_articles[0].source_domain == "example.com"
    assert len(company_articles) == 1
    assert company_articles[0].symbols == ("AAPL",)
    assert company_articles[0].category == NewsCategory.COMPANY
