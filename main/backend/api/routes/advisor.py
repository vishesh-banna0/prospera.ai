from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.api.dependencies import get_advisor_service
from backend.modules.advisor.application.dto import AdvisorReportView, AdvisorRequest
from backend.modules.advisor.application.services import AdvisorService

router = APIRouter(prefix="/advisor", tags=["advisor"])


@router.post("/summary", response_model=AdvisorReportView)
async def advisor_summary(
    request: AdvisorRequest,
    service: AdvisorService = Depends(get_advisor_service),
) -> AdvisorReportView:
    """Run the multi-agent Advisor over recent events and return short/long-term
    guidance plus a plain-English readout.

    Uses a LangGraph agent team (Analyst -> Strategist -> Writer), each on its
    own local model, falling back to deterministic logic when a model is
    unavailable. This can take several seconds while the models run.
    """
    try:
        return await service.generate(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Purpose:
# Expose the multi-agent AI Advisor over HTTP.
#
# Endpoints:
# - POST /advisor/summary: generate the advisory report from recent events.
