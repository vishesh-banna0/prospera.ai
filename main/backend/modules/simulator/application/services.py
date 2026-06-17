from __future__ import annotations

from backend.modules.simulator.application.commands import (
    AddVirtualCashUseCase,
    BuyStockUseCase,
    CreateEnvironmentUseCase,
    DeleteEnvironmentUseCase,
    RenameEnvironmentUseCase,
    SellStockUseCase,
    WithdrawVirtualCashUseCase,
)
from backend.modules.simulator.application.dto import (
    CashAdjustmentInput,
    CreateEnvironmentInput,
    RenameEnvironmentInput,
    TradeOrderInput,
)
from backend.modules.simulator.application.queries import (
    GetHoldingsUseCase,
    GetPortfolioPerformanceUseCase,
    GetTransactionsUseCase,
)
from backend.shared.types import EnvironmentId


class SimulatorService:
    """
    Stable simulator application boundary.

    Used by:
    - FastAPI routes
    - Future AI agents
    - RL environments
    - Background jobs
    """

    def __init__(
        self,
        create_environment: CreateEnvironmentUseCase,
        rename_environment: RenameEnvironmentUseCase,
        delete_environment: DeleteEnvironmentUseCase,
        add_virtual_cash: AddVirtualCashUseCase,
        withdraw_virtual_cash: WithdrawVirtualCashUseCase,
        buy_stock: BuyStockUseCase,
        sell_stock: SellStockUseCase,
        get_holdings: GetHoldingsUseCase,
        get_transactions: GetTransactionsUseCase,
        get_portfolio_performance: GetPortfolioPerformanceUseCase,
    ) -> None:
        self._create_environment = create_environment
        self._rename_environment = rename_environment
        self._delete_environment = delete_environment

        self._add_virtual_cash = add_virtual_cash
        self._withdraw_virtual_cash = withdraw_virtual_cash

        self._buy_stock = buy_stock
        self._sell_stock = sell_stock

        self._get_holdings = get_holdings
        self._get_transactions = get_transactions
        self._get_portfolio_performance = get_portfolio_performance

    async def create_environment(
        self,
        request: CreateEnvironmentInput,
    ) -> None:
        await self._create_environment.execute(request)

    async def rename_environment(
        self,
        request: RenameEnvironmentInput,
    ) -> None:
        await self._rename_environment.execute(request)

    async def delete_environment(
        self,
        environment_id: EnvironmentId,
    ) -> None:
        await self._delete_environment.execute(environment_id)

    async def add_virtual_cash(
        self,
        request: CashAdjustmentInput,
    ) -> None:
        await self._add_virtual_cash.execute(request)

    async def withdraw_virtual_cash(
        self,
        request: CashAdjustmentInput,
    ) -> None:
        await self._withdraw_virtual_cash.execute(request)

    async def buy_stock(
        self,
        request: TradeOrderInput,
    ) -> None:
        await self._buy_stock.execute(request)

    async def sell_stock(
        self,
        request: TradeOrderInput,
    ) -> None:
        await self._sell_stock.execute(request)

    async def get_holdings(
        self,
        environment_id: EnvironmentId,
    ):
        return await self._get_holdings.execute(
            environment_id,
        )

    async def get_transactions(
        self,
        environment_id: EnvironmentId,
    ):
        return await self._get_transactions.execute(
            environment_id,
        )

    async def get_portfolio_performance(
        self,
        environment_id: EnvironmentId,
    ):
        return await self._get_portfolio_performance.execute(
            environment_id,
        )

# Purpose:
# Defines higher-level simulator application services that group related use cases.
#
# Future Responsibilities:
# - Offer a cohesive interface for the API layer and future agent clients.
# - Coordinate commands and queries under a stable simulator service boundary.
# - Support future non-HTTP consumers such as internal jobs, AI agents, and RL runners.
#
# Dependencies:
# - backend.modules.simulator.application.commands
# - backend.modules.simulator.application.queries
#
# Future Classes:
# - SimulatorService
# - EnvironmentLifecycleService
# - PortfolioService
#
# What Should Not Live Here:
# - Domain entity definitions.
# - Provider SDK logic.
# - Persistence schema details.
