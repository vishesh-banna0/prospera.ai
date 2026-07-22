from __future__ import annotations

from collections.abc import Awaitable
from collections.abc import Callable

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
    CreateSipPlanInput,
    EnvironmentView,
    RenameEnvironmentInput,
    SipPlanView,
    TradeOrderInput,
)
from backend.modules.simulator.application.queries import (
    GetEnvironmentUseCase,
    GetHoldingsUseCase,
    GetPortfolioPerformanceUseCase,
    GetTransactionsUseCase,
)
from backend.modules.simulator.application.sip import (
    CancelSipPlanUseCase,
    CreateSipPlanUseCase,
    ExecuteDueSipInstallmentsUseCase,
    ListSipPlansUseCase,
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
        get_environment: GetEnvironmentUseCase,
        get_holdings: GetHoldingsUseCase,
        get_transactions: GetTransactionsUseCase,
        get_portfolio_performance: GetPortfolioPerformanceUseCase,
        create_sip_plan: CreateSipPlanUseCase | None = None,
        list_sip_plans: ListSipPlansUseCase | None = None,
        cancel_sip_plan: CancelSipPlanUseCase | None = None,
        execute_due_sip: ExecuteDueSipInstallmentsUseCase | None = None,
        commit: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self._commit = commit
        self._create_environment = create_environment
        self._rename_environment = rename_environment
        self._delete_environment = delete_environment

        self._add_virtual_cash = add_virtual_cash
        self._withdraw_virtual_cash = withdraw_virtual_cash

        self._buy_stock = buy_stock
        self._sell_stock = sell_stock

        self._get_environment = get_environment
        self._get_holdings = get_holdings
        self._get_transactions = get_transactions
        self._get_portfolio_performance = get_portfolio_performance

        self._create_sip_plan = create_sip_plan
        self._list_sip_plans = list_sip_plans
        self._cancel_sip_plan = cancel_sip_plan
        self._execute_due_sip = execute_due_sip

    async def create_environment(
        self,
        request: CreateEnvironmentInput,
    ) -> EnvironmentView:
        view = await self._create_environment.execute(request)
        await self._commit_changes()
        return view

    async def get_environment(
        self,
        environment_id: EnvironmentId,
    ) -> EnvironmentView:
        return await self._get_environment.execute(environment_id)

    async def rename_environment(
        self,
        request: RenameEnvironmentInput,
    ) -> None:
        await self._rename_environment.execute(request)
        await self._commit_changes()

    async def delete_environment(
        self,
        environment_id: EnvironmentId,
    ) -> None:
        await self._delete_environment.execute(environment_id)
        await self._commit_changes()

    async def add_virtual_cash(
        self,
        request: CashAdjustmentInput,
    ) -> None:
        await self._add_virtual_cash.execute(request)
        await self._commit_changes()

    async def withdraw_virtual_cash(
        self,
        request: CashAdjustmentInput,
    ) -> None:
        await self._withdraw_virtual_cash.execute(request)
        await self._commit_changes()

    async def buy_stock(
        self,
        request: TradeOrderInput,
    ) -> None:
        await self._buy_stock.execute(request)
        await self._commit_changes()

    async def sell_stock(
        self,
        request: TradeOrderInput,
    ) -> None:
        await self._sell_stock.execute(request)
        await self._commit_changes()

    async def _commit_changes(self) -> None:
        if self._commit is not None:
            await self._commit()

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
        # Any SIP installments that have come due are executed here (lazy
        # catch-up) so a portfolio read is always current before we value it.
        await self._run_due_sip(environment_id)
        return await self._get_portfolio_performance.execute(
            environment_id,
        )

    async def _run_due_sip(
        self,
        environment_id: EnvironmentId,
    ) -> None:
        if self._execute_due_sip is None:
            return
        executed = await self._execute_due_sip.execute(environment_id)
        if executed:
            await self._commit_changes()

    async def create_sip_plan(
        self,
        request: CreateSipPlanInput,
    ) -> SipPlanView:
        if self._create_sip_plan is None:
            raise RuntimeError("SIP plans are not configured.")
        view = await self._create_sip_plan.execute(request)
        await self._commit_changes()
        return view

    async def list_sip_plans(
        self,
        environment_id: EnvironmentId,
    ) -> list[SipPlanView]:
        if self._list_sip_plans is None:
            return []
        # A pure read: due installments are executed only in
        # get_portfolio_performance, so the catch-up runs in exactly one place and
        # can't race itself when the page loads both in parallel. The performance
        # read (and the refresh after any create/cancel) keeps this list current.
        return await self._list_sip_plans.execute(environment_id)

    async def cancel_sip_plan(
        self,
        environment_id: EnvironmentId,
        plan_id: str,
    ) -> None:
        if self._cancel_sip_plan is None:
            raise RuntimeError("SIP plans are not configured.")
        await self._cancel_sip_plan.execute(environment_id, plan_id)
        await self._commit_changes()

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
