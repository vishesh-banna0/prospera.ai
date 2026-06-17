from __future__ import annotations

from backend.modules.market_data.application.services import MarketDataService
from backend.modules.simulator.application.dto import (
    HoldingView,
    PortfolioPerformanceView,
    TransactionView,
)
from backend.modules.simulator.domain.repositories import (
    EnvironmentRepository,
    HoldingRepository,
    TransactionRepository,
)
from backend.shared.types import EnvironmentId


class GetHoldingsUseCase:
    """
    Retrieve all holdings belonging to an environment.
    """

    def __init__(
        self,
        holding_repository: HoldingRepository,
    ) -> None:
        self._holding_repository = holding_repository

    async def execute(
        self,
        environment_id: EnvironmentId,
    ) -> list[HoldingView]:
        raise NotImplementedError


class GetTransactionsUseCase:
    """
    Retrieve transaction history for an environment.
    """

    def __init__(
        self,
        transaction_repository: TransactionRepository,
    ) -> None:
        self._transaction_repository = transaction_repository

    async def execute(
        self,
        environment_id: EnvironmentId,
    ) -> list[TransactionView]:
        raise NotImplementedError


class GetPortfolioPerformanceUseCase:
    """
    Build a portfolio performance view using:
    - holdings
    - cash balance
    - current market prices
    """

    def __init__(
        self,
        environment_repository: EnvironmentRepository,
        holding_repository: HoldingRepository,
        market_data_service: MarketDataService,
    ) -> None:
        self._environment_repository = environment_repository
        self._holding_repository = holding_repository
        self._market_data_service = market_data_service

    async def execute(
        self,
        environment_id: EnvironmentId,
    ) -> PortfolioPerformanceView:
        raise NotImplementedError

# Purpose:
# Placeholder module for simulator read-only use cases.
#
# Future Responsibilities:
# - Fetch holdings for a specific environment.
# - Fetch transaction history for a specific environment.
# - Build portfolio performance views using current market prices from the shared service.
#
# Dependencies:
# - backend.modules.simulator.application.dto
# - backend.modules.simulator.domain.repositories
# - backend.modules.market_data.application.services
#
# Future Classes / Functions:
# - GetHoldingsUseCase
# - GetTransactionsUseCase
# - GetPortfolioPerformanceUseCase
#
# What Should Not Live Here:
# - Mutation workflows.
# - HTTP response serialization.
# - Direct cache management.
