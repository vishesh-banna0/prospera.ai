from __future__ import annotations

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Literal

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query

from backend.api.dependencies import get_news_intelligence_service
from backend.modules.news.application.dto import (
    NewsArticleView,
    NewsArticlesView,
    NewsQueryRequest,
    NewsWarehouseStatsView,
    SyncNewsRequest,
    SyncNewsView,
)
from backend.modules.news.application.services import NewsIntelligenceService

router = APIRouter(prefix="/news", tags=["news"])


@router.post("/sync", response_model=SyncNewsView)
async def sync_news(
    request: SyncNewsRequest,
    service: NewsIntelligenceService = Depends(get_news_intelligence_service),
) -> SyncNewsView:
    """Collect, deduplicate, clean, classify, and store news articles."""
    try:
        return await service.sync_news(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/articles", response_model=NewsArticlesView)
async def list_news_articles(
    category: Literal["global", "india", "company", "sector"] | None = Query(
        default=None,
        description="News bucket. Use sector for sector news; put values like Technology in the sector field.",
    ),
    symbol: str | None = Query(
        default=None,
        description="Ticker symbol filter, for example AAPL or GOOGL.",
    ),
    sector: str | None = Query(
        default=None,
        description="Business sector filter, for example Technology or Financial Services.",
    ),
    country: str | None = Query(
        default=None,
        description="Country code filter, for example IN or US.",
    ),
    query: str | None = Query(
        default=None,
        description="Free-text search across title, summary, and body.",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: NewsIntelligenceService = Depends(get_news_intelligence_service),
) -> NewsArticlesView:
    """List articles from the internal news warehouse."""
    try:
        return await service.list_articles(
            NewsQueryRequest(
                category=category,
                symbol=symbol,
                sector=sector,
                country=country,
                query=query,
                limit=limit,
                offset=offset,
            )
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/global", response_model=NewsArticlesView)
async def list_global_news(
    limit: int = 50,
    offset: int = 0,
    service: NewsIntelligenceService = Depends(get_news_intelligence_service),
) -> NewsArticlesView:
    """List global news from the warehouse."""
    return await service.list_articles(
        NewsQueryRequest(category="global", limit=limit, offset=offset)
    )


@router.get("/india", response_model=NewsArticlesView)
async def list_indian_news(
    limit: int = 50,
    offset: int = 0,
    service: NewsIntelligenceService = Depends(get_news_intelligence_service),
) -> NewsArticlesView:
    """List Indian market news from the warehouse."""
    return await service.list_articles(
        NewsQueryRequest(category="india", country="IN", limit=limit, offset=offset)
    )


@router.get("/company/{symbol}", response_model=NewsArticlesView)
async def list_company_news(
    symbol: str,
    limit: int = 50,
    offset: int = 0,
    service: NewsIntelligenceService = Depends(get_news_intelligence_service),
) -> NewsArticlesView:
    """List company news from the warehouse."""
    return await service.list_articles(
        NewsQueryRequest(
            category="company",
            symbol=symbol,
            limit=limit,
            offset=offset,
        )
    )


@router.post("/company/{symbol}/sync", response_model=SyncNewsView)
async def sync_company_news(
    symbol: str,
    lookback_days: int = Query(
        default=4,
        ge=1,
        le=30,
        description="How many recent calendar days to fetch for this company.",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    service: NewsIntelligenceService = Depends(get_news_intelligence_service),
) -> SyncNewsView:
    """Sync recent company news into the warehouse before analysis."""
    end_at = datetime.now(UTC)
    start_at = end_at - timedelta(days=lookback_days)
    try:
        return await service.sync_news(
            SyncNewsRequest(
                categories=("company",),
                symbols=(symbol,),
                start_at=start_at,
                end_at=end_at,
                limit=limit,
            )
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sector/{sector}", response_model=NewsArticlesView)
async def list_sector_news(
    sector: str,
    limit: int = 50,
    offset: int = 0,
    service: NewsIntelligenceService = Depends(get_news_intelligence_service),
) -> NewsArticlesView:
    """List sector news from the warehouse."""
    return await service.list_articles(
        NewsQueryRequest(
            category="sector",
            sector=sector,
            limit=limit,
            offset=offset,
        )
    )


@router.get("/warehouse/stats", response_model=NewsWarehouseStatsView)
async def get_news_warehouse_stats(
    service: NewsIntelligenceService = Depends(get_news_intelligence_service),
) -> NewsWarehouseStatsView:
    """Get article counts for the news warehouse."""
    return await service.get_warehouse_stats()


@router.get("/articles/{article_id}", response_model=NewsArticleView)
async def get_news_article(
    article_id: str,
    service: NewsIntelligenceService = Depends(get_news_intelligence_service),
) -> NewsArticleView:
    """Get one warehouse article by id."""
    try:
        return await service.get_article(article_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
