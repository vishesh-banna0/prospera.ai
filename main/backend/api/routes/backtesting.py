from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.api.dependencies import get_backtest_service
from backend.modules.backtesting.application.dto import (
    BacktestResultView,
    LumpSumRequest,
    SipRequest,
)
from backend.modules.backtesting.application.services import BacktestService

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.post("/lumpsum", response_model=BacktestResultView)
async def backtest_lump_sum(
    request: LumpSumRequest,
    service: BacktestService = Depends(get_backtest_service),
) -> BacktestResultView:
    """Simulate a one-time investment (e.g. 'if I invested 100000 in NVDA 5y ago')."""
    try:
        return await service.run_lump_sum(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sip", response_model=BacktestResultView)
async def backtest_sip(
    request: SipRequest,
    service: BacktestService = Depends(get_backtest_service),
) -> BacktestResultView:
    """Simulate a monthly SIP (e.g. 'if I invested 5000 monthly for 10 years')."""
    try:
        return await service.run_sip(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


"""
Purpose:
Expose Phase 15 historical investment simulation over HTTP.

Endpoints:
- POST /backtest/lumpsum: One-time investment simulation
- POST /backtest/sip: Systematic (monthly) investment simulation

Both return return metrics (total return, CAGR, XIRR), risk metrics (volatility,
Sharpe, Sortino, max drawdown), and a sampled equity curve. Values are in INR.

What Should Not Live Here:
- The simulation engine (domain/engine.py) or metric math (domain/metrics.py).
"""
