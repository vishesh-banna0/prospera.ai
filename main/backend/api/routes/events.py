from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query

from backend.api.dependencies import get_event_extraction_service
from backend.modules.events.application.dto import (
    EventQueryRequest,
    EventStatsView,
    EventView,
    EventsView,
    ExtractEventsRequest,
    ExtractEventsView,
)
from backend.modules.events.application.services import EventExtractionService

router = APIRouter(prefix="/events", tags=["events"])


@router.post("/extract", response_model=ExtractEventsView)
async def extract_events(
    request: ExtractEventsRequest,
    service: EventExtractionService = Depends(get_event_extraction_service),
) -> ExtractEventsView:
    """Run event extraction over selected warehouse articles and store results."""
    try:
        return await service.extract_events(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=EventsView)
async def list_events(
    event_type: str | None = Query(
        default=None,
        description="Event type filter, e.g. earnings_beat, merger_acquisition, ipo.",
    ),
    symbol: str | None = Query(
        default=None,
        description="Ticker symbol filter, for example AAPL.",
    ),
    sector: str | None = Query(
        default=None,
        description="Business sector filter, for example Technology.",
    ),
    sentiment: Literal["positive", "negative", "neutral"] | None = Query(
        default=None,
        description="Sentiment filter.",
    ),
    importance: Literal["high", "medium", "low"] | None = Query(
        default=None,
        description="Importance filter.",
    ),
    start_at: datetime | None = Query(
        default=None,
        description="Only events on or after this timestamp.",
    ),
    end_at: datetime | None = Query(
        default=None,
        description="Only events on or before this timestamp.",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: EventExtractionService = Depends(get_event_extraction_service),
) -> EventsView:
    """List structured events from the event warehouse."""
    try:
        return await service.list_events(
            EventQueryRequest(
                event_type=event_type,
                symbol=symbol,
                sector=sector,
                sentiment=sentiment,
                importance=importance,
                start_at=start_at,
                end_at=end_at,
                limit=limit,
                offset=offset,
            )
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stats", response_model=EventStatsView)
async def get_event_stats(
    service: EventExtractionService = Depends(get_event_extraction_service),
) -> EventStatsView:
    """Get total and per-type counts for the event warehouse."""
    return await service.get_stats()


@router.get("/company/{symbol}", response_model=EventsView)
async def list_company_events(
    symbol: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: EventExtractionService = Depends(get_event_extraction_service),
) -> EventsView:
    """List events extracted for a specific company symbol."""
    return await service.list_events(
        EventQueryRequest(symbol=symbol, limit=limit, offset=offset)
    )


@router.get("/{event_id}", response_model=EventView)
async def get_event(
    event_id: str,
    service: EventExtractionService = Depends(get_event_extraction_service),
) -> EventView:
    """Get one structured event by id."""
    try:
        return await service.get_event(event_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


"""
Purpose:
Expose Phase 8 event extraction and the structured-event warehouse over HTTP.

Endpoints:
- POST /events/extract: Run extraction over selected articles, store events
- GET /events: List/filter structured events
- GET /events/stats: Event counts by type
- GET /events/company/{symbol}: Events for one company
- GET /events/{event_id}: Fetch one event

What Should Not Live Here:
- Extraction logic (belongs in an extractor adapter)
- Persistence queries
- Sentiment/importance rules
"""
