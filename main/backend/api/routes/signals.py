from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.dependencies import get_signal_fusion_service
from backend.modules.signals.application.dto import (
    FusedSignalsView,
    FusedSignalView,
    FuseSignalRequest,
)
from backend.modules.signals.application.services import SignalFusionService

router = APIRouter(prefix="/signals", tags=["signals"])


@router.post("/fuse/{symbol}", response_model=FusedSignalView)
async def fuse_signal(
    symbol: str,
    event_limit: int = Query(default=50, ge=1, le=200),
    service: SignalFusionService = Depends(get_signal_fusion_service),
) -> FusedSignalView:
    """Blend news + company + prediction signals into a Buy/Hold/Sell call."""
    try:
        return await service.fuse_signal(
            FuseSignalRequest(symbol=symbol, event_limit=event_limit)
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=FusedSignalsView)
async def list_signals(
    limit: int = Query(default=50, ge=1, le=200),
    service: SignalFusionService = Depends(get_signal_fusion_service),
) -> FusedSignalsView:
    """List the latest fused signal per symbol, most recent first."""
    return await service.list_signals(limit=limit)


@router.get("/{symbol}", response_model=FusedSignalView)
async def get_signal(
    symbol: str,
    service: SignalFusionService = Depends(get_signal_fusion_service),
) -> FusedSignalView:
    """Get the latest stored fused signal for one symbol."""
    try:
        return await service.get_signal(symbol)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


"""
Purpose:
Expose Phase 13 signal fusion (unified Buy/Hold/Sell) over HTTP.

Endpoints:
- POST /signals/fuse/{symbol}: Blend the latest upstream signals and store
- GET /signals: List latest fused signals
- GET /signals/{symbol}: Latest fused signal for one symbol

What Should Not Live Here:
- Blending math (domain/fusion.py) or signal gathering (application service).
"""
