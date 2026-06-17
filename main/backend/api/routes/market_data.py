from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.api.dependencies import get_market_data_service
from backend.modules.market_data.application.dto import (
    QuoteRequest,
    QuoteView,
    SymbolSearchRequest,
    InstrumentSearchResultsView,
    MarketMetadataView,
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
