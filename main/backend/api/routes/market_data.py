from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from backend.api.dependencies import get_market_data_service
from backend.modules.market_data.application.dto import (
    CompanyProfileView,
    HistoricalPriceRequest,
    HistoricalPriceSeriesView,
    InstrumentSearchResultsView,
    MarketMetadataView,
    QuoteRequest,
    QuoteView,
    SyncHistoricalPricesRequest,
    SyncHistoricalPricesView,
    SymbolSearchRequest,
)
from backend.modules.market_data.application.services import MarketDataService

router = APIRouter(prefix="/market-data", tags=["market_data"])


@router.get("/quote/{symbol}", response_model=QuoteView)
async def get_quote(
    symbol: str,
    service: MarketDataService = Depends(get_market_data_service),
) -> QuoteView:
    """Get current market quote for a symbol."""
    try:
        request = QuoteRequest(symbol=symbol)
        quote = await service.get_quote(request)
        return quote
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/history/{symbol}", response_model=HistoricalPriceSeriesView)
async def get_historical_prices(
    symbol: str,
    start_at: datetime,
    end_at: datetime,
    auto_sync: bool = True,
    service: MarketDataService = Depends(get_market_data_service),
) -> HistoricalPriceSeriesView:
    """Get normalized daily historical prices for a symbol."""
    try:
        request = HistoricalPriceRequest(
            symbol=symbol,
            start_at=start_at,
            end_at=end_at,
            auto_sync=auto_sync,
        )
        return await service.get_historical_prices(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/history/sync", response_model=SyncHistoricalPricesView)
async def sync_historical_prices(
    request: SyncHistoricalPricesRequest,
    service: MarketDataService = Depends(get_market_data_service),
) -> SyncHistoricalPricesView:
    """Synchronize historical prices into the internal market data warehouse."""
    try:
        return await service.sync_historical_prices(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/search", response_model=InstrumentSearchResultsView)
async def search_symbols(
    request: SymbolSearchRequest,
    service: MarketDataService = Depends(get_market_data_service),
) -> InstrumentSearchResultsView:
    """Search for instruments by query."""
    try:
        results = await service.search_symbols(request)
        return results
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/profile/{symbol}", response_model=CompanyProfileView)
async def get_company_profile(
    symbol: str,
    service: MarketDataService = Depends(get_market_data_service),
) -> CompanyProfileView:
    """Get normalized company metadata for a symbol."""
    try:
        return await service.get_company_profile(symbol)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/metadata", response_model=MarketMetadataView)
async def get_market_metadata(
    service: MarketDataService = Depends(get_market_data_service),
) -> MarketMetadataView:
    """Get market metadata (supported exchanges, currencies, timezone)."""
    try:
        metadata = await service.get_market_metadata()
        return metadata
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


"""
Purpose:
Expose read-only endpoints for current prices, historical prices, and symbol search.

Responsibilities:
- Expose read-only endpoints for market data
- Ensure every consumer uses central market data service
- Provide stable contract for simulator and agents
- Handle HTTP error responses

Dependencies:
- backend.api.dependencies (get_market_data_service)
- backend.modules.market_data.application.services
- backend.modules.market_data.application.dto

Endpoints:
- GET /market-data/quote/{symbol}: Current market quote
- POST /market-data/search: Search instruments by query
- GET /market-data/metadata: Market metadata

What Should Not Live Here:
- Vendor-specific authentication
- Simulator environment logic
- Direct caching implementation
"""
