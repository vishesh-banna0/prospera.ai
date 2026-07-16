from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from dataclasses import replace

from backend.api.dependencies import get_simulator_service
from backend.modules.simulator.application.dto import (
    CashAdjustmentInput,
    HoldingView,
    TradeOrderInput,
    TransactionView,
    PortfolioPerformanceView,
)
from backend.modules.simulator.application.services import SimulatorService
from backend.shared.types import EnvironmentId

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.post("/{environment_id}/cash/deposit")
async def add_virtual_cash(
    environment_id: EnvironmentId,
    request: CashAdjustmentInput,
    service: SimulatorService = Depends(get_simulator_service),
) -> dict:
    """Deposit virtual cash into environment."""
    try:
        request = replace(request, environment_id=environment_id)
        await service.add_virtual_cash(request)
        return {"status": "deposited", "amount": str(request.amount.amount)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{environment_id}/cash/withdraw")
async def withdraw_virtual_cash(
    environment_id: EnvironmentId,
    request: CashAdjustmentInput,
    service: SimulatorService = Depends(get_simulator_service),
) -> dict:
    """Withdraw virtual cash from environment."""
    try:
        request = replace(request, environment_id=environment_id)
        await service.withdraw_virtual_cash(request)
        return {"status": "withdrawn", "amount": str(request.amount.amount)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{environment_id}/buy")
async def buy_stock(
    environment_id: EnvironmentId,
    request: TradeOrderInput,
    service: SimulatorService = Depends(get_simulator_service),
) -> dict:
    """Buy stock in environment."""
    try:
        request = replace(request, environment_id=environment_id)
        await service.buy_stock(request)
        return {"status": "order_placed", "symbol": request.symbol, "quantity": request.quantity}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{environment_id}/sell")
async def sell_stock(
    environment_id: EnvironmentId,
    request: TradeOrderInput,
    service: SimulatorService = Depends(get_simulator_service),
) -> dict:
    """Sell stock in environment."""
    try:
        request = replace(request, environment_id=environment_id)
        await service.sell_stock(request)
        return {"status": "order_placed", "symbol": request.symbol, "quantity": request.quantity}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{environment_id}/holdings", response_model=list[HoldingView])
async def list_holdings(
    environment_id: EnvironmentId,
    service: SimulatorService = Depends(get_simulator_service),
) -> list[HoldingView]:
    """Get all holdings in environment."""
    try:
        holdings = await service.get_holdings(environment_id)
        return holdings
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{environment_id}/transactions", response_model=list[TransactionView])
async def list_transactions(
    environment_id: EnvironmentId,
    service: SimulatorService = Depends(get_simulator_service),
) -> list[TransactionView]:
    """Get transaction history for environment."""
    try:
        transactions = await service.get_transactions(environment_id)
        return transactions
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{environment_id}/performance", response_model=PortfolioPerformanceView)
async def get_performance(
    environment_id: EnvironmentId,
    service: SimulatorService = Depends(get_simulator_service),
) -> PortfolioPerformanceView:
    """Get portfolio performance metrics."""
    try:
        performance = await service.get_portfolio_performance(environment_id)
        return performance
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


"""
Purpose:
Expose virtual cash, trading, holdings, and transaction endpoints.

Responsibilities:
- Expose virtual cash deposit and withdrawal actions
- Expose buy and sell trading actions
- Expose read endpoints for holdings, transactions, and performance
- Handle HTTP error responses

Dependencies:
- backend.api.dependencies (get_simulator_service)
- backend.modules.simulator.application.commands
- backend.modules.simulator.application.queries
- backend.modules.simulator.application.dto

Endpoints:
- POST /portfolios/{environment_id}/cash/deposit: Add cash
- POST /portfolios/{environment_id}/cash/withdraw: Remove cash
- POST /portfolios/{environment_id}/buy: Buy stock
- POST /portfolios/{environment_id}/sell: Sell stock
- GET /portfolios/{environment_id}/holdings: List holdings
- GET /portfolios/{environment_id}/transactions: Transaction history
- GET /portfolios/{environment_id}/performance: Performance metrics

What Should Not Live Here:
- Trading rules
- Cost basis calculations
- External symbol search
"""
