from __future__ import annotations

from backend.modules.market_data.application.services import MarketDataService
from backend.modules.simulator.application.dto import (
    CashAdjustmentInput,
    CreateEnvironmentInput,
    RenameEnvironmentInput,
    TradeOrderInput,
)
from backend.modules.simulator.domain.repositories import (
    EnvironmentRepository,
    HoldingRepository,
    TransactionRepository,
)


class CreateEnvironmentUseCase:

    def __init__(
        self,
        environment_repository: EnvironmentRepository,
    ) -> None:
        self._environment_repository = environment_repository

    async def execute(
        self,
        request: CreateEnvironmentInput,
    ) -> None:
        raise NotImplementedError


class RenameEnvironmentUseCase:

    def __init__(
        self,
        environment_repository: EnvironmentRepository,
    ) -> None:
        self._environment_repository = environment_repository

    async def execute(
        self,
        request: RenameEnvironmentInput,
    ) -> None:
        raise NotImplementedError


class DeleteEnvironmentUseCase:

    def __init__(
        self,
        environment_repository: EnvironmentRepository,
    ) -> None:
        self._environment_repository = environment_repository

    async def execute(
        self,
        environment_id: str,
    ) -> None:
        raise NotImplementedError


class AddVirtualCashUseCase:

    def __init__(
        self,
        environment_repository: EnvironmentRepository,
        transaction_repository: TransactionRepository,
    ) -> None:
        self._environment_repository = environment_repository
        self._transaction_repository = transaction_repository

    async def execute(
        self,
        request: CashAdjustmentInput,
    ) -> None:
        raise NotImplementedError


class WithdrawVirtualCashUseCase:

    def __init__(
        self,
        environment_repository: EnvironmentRepository,
        transaction_repository: TransactionRepository,
    ) -> None:
        self._environment_repository = environment_repository
        self._transaction_repository = transaction_repository

    async def execute(
        self,
        request: CashAdjustmentInput,
    ) -> None:
        raise NotImplementedError


class BuyStockUseCase:

    def __init__(
        self,
        environment_repository: EnvironmentRepository,
        holding_repository: HoldingRepository,
        transaction_repository: TransactionRepository,
        market_data_service: MarketDataService,
    ) -> None:
        self._environment_repository = environment_repository
        self._holding_repository = holding_repository
        self._transaction_repository = transaction_repository
        self._market_data_service = market_data_service

    async def execute(
        self,
        request: TradeOrderInput,
    ) -> None:
        raise NotImplementedError


class SellStockUseCase:

    def __init__(
        self,
        environment_repository: EnvironmentRepository,
        holding_repository: HoldingRepository,
        transaction_repository: TransactionRepository,
        market_data_service: MarketDataService,
    ) -> None:
        self._environment_repository = environment_repository
        self._holding_repository = holding_repository
        self._transaction_repository = transaction_repository
        self._market_data_service = market_data_service

    async def execute(
        self,
        request: TradeOrderInput,
    ) -> None:
        raise NotImplementedError
# Purpose:
# Placeholder module for simulator state-changing use cases.
#
# Future Responsibilities:
# - Handle environment creation, rename, and deletion.
# - Handle virtual cash deposits and withdrawals.
# - Handle buy and sell order orchestration using market data from the shared service.
#
# Dependencies:
# - backend.modules.simulator.application.dto
# - backend.modules.simulator.domain.repositories
# - backend.modules.simulator.domain.policies
# - backend.modules.market_data.application.services
#
# Future Classes / Functions:
# - CreateEnvironmentUseCase
# - RenameEnvironmentUseCase
# - DeleteEnvironmentUseCase
# - AddVirtualCashUseCase
# - WithdrawVirtualCashUseCase
# - BuyStockUseCase
# - SellStockUseCase
#
# What Should Not Live Here:
# - Raw SQL queries.
# - API request parsing.
# - Direct external vendor access.
