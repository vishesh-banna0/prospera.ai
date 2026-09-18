from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.api.dependencies import get_portfolio_optimization_service
from backend.modules.portfolio.application.dto import (
    OptimizePortfolioRequest,
    PortfolioOptimizationView,
    PortfolioRiskRequest,
    PortfolioRiskView,
)
from backend.modules.portfolio.application.services import (
    PortfolioOptimizationService,
)

router = APIRouter(prefix="/portfolio", tags=["portfolio-optimization"])


@router.post("/optimize", response_model=PortfolioOptimizationView)
async def optimize_portfolio(
    request: OptimizePortfolioRequest,
    service: PortfolioOptimizationService = Depends(
        get_portfolio_optimization_service
    ),
) -> PortfolioOptimizationView:
    """Solve for target portfolio weights and explain the resulting risk.

    Objectives: ``max_sharpe`` (default), ``min_variance``,
    ``inverse_volatility``, ``equal_weight``. All are long-only and fully
    invested, with ``max_weight`` capping any single position.

    Pass ``symbols`` to optimize a candidate basket, or ``environment_id`` to
    optimize what a simulator environment actually holds — in which case the
    response also carries current weights and the rebalancing trades that
    would reach the target.

    Every result reports an equal-weight baseline alongside it, so it is
    visible whether the optimization actually earned its estimation error.
    """
    try:
        return await service.optimize(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # pragma: no cover - unexpected upstream failure
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/risk", response_model=PortfolioRiskView)
async def analyze_portfolio_risk(
    request: PortfolioRiskRequest,
    service: PortfolioOptimizationService = Depends(
        get_portfolio_optimization_service
    ),
) -> PortfolioRiskView:
    """Risk decomposition of an environment's holdings exactly as they stand.

    Reports portfolio volatility, Sharpe, diversification ratio, effective
    number of assets, max drawdown, the correlation matrix, and each
    position's share of total risk — which is not the same as its share of
    capital. Concentration warnings call out positions that dominate either.
    """
    try:
        return await service.analyze_holdings(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # pragma: no cover - unexpected upstream failure
        raise HTTPException(status_code=500, detail=str(e))


"""
Purpose:
Expose portfolio construction and portfolio-level risk analytics over HTTP.

Endpoints:
- POST /portfolio/optimize: target weights, risk decomposition, rebalance trades
- POST /portfolio/risk: risk analytics for currently held positions

What Should Not Live Here:
- Optimization math (modules/portfolio/domain/optimizer.py).
- Risk math (modules/portfolio/domain/risk.py).
- Trade execution — these endpoints recommend; the simulator executes.
"""
