from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.dependencies import get_company_intelligence_service
from backend.modules.company.application.dto import (
    AnalyzeCompanyRequest,
    CompanyScoresView,
    CompanyScoreView,
)
from backend.modules.company.application.services import CompanyIntelligenceService

router = APIRouter(prefix="/company", tags=["company"])


@router.post("/analyze/{symbol}", response_model=CompanyScoreView)
async def analyze_company(
    symbol: str,
    lookback_days: int = Query(default=180, ge=5, le=2000),
    event_limit: int = Query(default=50, ge=1, le=200),
    service: CompanyIntelligenceService = Depends(get_company_intelligence_service),
) -> CompanyScoreView:
    """Score one company from its price history and recent news events."""
    try:
        return await service.analyze(
            AnalyzeCompanyRequest(
                symbol=symbol, lookback_days=lookback_days, event_limit=event_limit
            )
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=CompanyScoresView)
async def list_companies(
    limit: int = Query(default=50, ge=1, le=200),
    service: CompanyIntelligenceService = Depends(get_company_intelligence_service),
) -> CompanyScoresView:
    """List the latest scorecard for each analyzed company, best first."""
    return await service.list_companies(limit=limit)


@router.get("/{symbol}", response_model=CompanyScoreView)
async def get_company(
    symbol: str,
    service: CompanyIntelligenceService = Depends(get_company_intelligence_service),
) -> CompanyScoreView:
    """Get the latest stored scorecard for one company."""
    try:
        return await service.get_company(symbol)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


"""
Purpose:
Expose Phase 10 company intelligence scoring over HTTP.

Endpoints:
- POST /company/analyze/{symbol}: Score a company now and store the result
- GET /company: List latest scorecards (ranked)
- GET /company/{symbol}: Fetch the latest stored scorecard

What Should Not Live Here:
- Scoring math (domain/scoring.py)
- Persistence queries
"""
