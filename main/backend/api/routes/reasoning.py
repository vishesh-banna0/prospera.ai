from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.dependencies import get_reasoning_service
from backend.modules.reasoning.application.dto import (
    AnalyzeReasoningRequest,
    ReasonedOpinionsView,
    ReasonedOpinionView,
)
from backend.modules.reasoning.application.services import ReasoningService

router = APIRouter(prefix="/reasoning", tags=["reasoning"])


@router.post("/analyze/{symbol}", response_model=ReasonedOpinionView)
async def analyze_reasoning(
    symbol: str,
    event_limit: int = Query(default=10, ge=1, le=100),
    research_top_k: int = Query(default=3, ge=0, le=20),
    service: ReasoningService = Depends(get_reasoning_service),
) -> ReasonedOpinionView:
    """Produce an explainable bullish/bearish/neutral opinion for a symbol."""
    try:
        return await service.analyze(
            AnalyzeReasoningRequest(
                symbol=symbol, event_limit=event_limit, research_top_k=research_top_k
            )
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=ReasonedOpinionsView)
async def list_reasoning(
    limit: int = Query(default=50, ge=1, le=200),
    service: ReasoningService = Depends(get_reasoning_service),
) -> ReasonedOpinionsView:
    """List the latest opinion per symbol, most recent first."""
    return await service.list_opinions(limit=limit)


@router.get("/{symbol}", response_model=ReasonedOpinionView)
async def get_reasoning(
    symbol: str,
    service: ReasoningService = Depends(get_reasoning_service),
) -> ReasonedOpinionView:
    """Get the latest stored opinion for one symbol."""
    try:
        return await service.get_opinion(symbol)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


"""
Purpose:
Expose Phase 11 explainable reasoning over HTTP.

Endpoints:
- POST /reasoning/analyze/{symbol}: Reason over gathered evidence and store
- GET /reasoning: List latest opinions
- GET /reasoning/{symbol}: Latest opinion for one symbol

What Should Not Live Here:
- Reasoner logic (infrastructure/reasoners.py) or evidence gathering (service).
"""
