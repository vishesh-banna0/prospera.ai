from __future__ import annotations

from decimal import Decimal

from backend.modules.market_data.application.services import MarketDataService
from backend.modules.market_data.application.dto import QuoteRequest
from backend.modules.simulator.application.dto import (
    HoldingView,
    PortfolioPerformanceView,
    TransactionView,
)
from backend.modules.simulator.domain.policies import (
    calculate_unrealized_pnl,
    calculate_market_value,
)
from backend.modules.simulator.domain.repositories import (
    EnvironmentRepository,
    HoldingRepository,
    TransactionRepository,
)
from backend.modules.simulator.domain.value_objects import ShareQuantity
from backend.shared.types import EnvironmentId, Money


class GetHoldingsUseCase:
    """Retrieve all holdings belonging to an environment."""

    def __init__(
        self,
        holding_repository: HoldingRepository,
    ) -> None:
        self._holding_repository = holding_repository

    async def execute(
        self,
        environment_id: EnvironmentId,
    ) -> list[HoldingView]:
        holdings = await self._holding_repository.list_by_environment(
            environment_id
        )
        views = []
        for holding in holdings:
            view = HoldingView(
                symbol=holding.symbol,
                quantity=float(holding.quantity.value),
                average_cost=str(holding.average_cost.amount),
                market_value=None,
                unrealized_pnl=None,
                return_percentage=None,
            )
            views.append(view)
        return views


class GetTransactionsUseCase:
    """Retrieve transaction history for an environment."""

    def __init__(
        self,
        transaction_repository: TransactionRepository,
    ) -> None:
        self._transaction_repository = transaction_repository

    async def execute(
        self,
        environment_id: EnvironmentId,
    ) -> list[TransactionView]:
        transactions = await self._transaction_repository.list_by_environment(
            environment_id
        )
        views = []
        for transaction in transactions:
            view = TransactionView(
                transaction_id=transaction.transaction_id,
                symbol=transaction.symbol,
                transaction_type=transaction.transaction_type,
                quantity=float(transaction.quantity.value) if transaction.quantity else None,
                amount=str(transaction.amount.amount),
                executed_at=transaction.executed_at,
            )
            views.append(view)
        return views


class GetPortfolioPerformanceUseCase:
    """Build a portfolio performance view using holdings, cash balance, and current market prices."""

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
        environment = await self._environment_repository.get(environment_id)
        if environment is None:
            raise ValueError(f"Environment {environment_id} not found")

        holdings = await self._holding_repository.list_by_environment(
            environment_id
        )

        total_market_value = Decimal("0")
        total_invested_amount = Decimal("0")
        total_unrealized_pnl = Decimal("0")

        for holding in holdings:
            try:
                quote = await self._market_data_service.get_quote(
                    QuoteRequest(symbol=holding.symbol)
                )
                current_price = Money(
                    amount=Decimal(str(quote.last_price)),
                    currency=quote.currency,
                )
            except Exception:
                current_price = holding.average_cost

            market_value = calculate_market_value(
                holding.quantity,
                current_price,
            )
            total_market_value += market_value.amount

            invested_value = Money(
                amount=holding.average_cost.amount * holding.quantity.value,
                currency=holding.average_cost.currency,
            )
            total_invested_amount += invested_value.amount

            unrealized_pnl = calculate_unrealized_pnl(
                holding.quantity,
                holding.average_cost,
                current_price,
            )
            total_unrealized_pnl += unrealized_pnl.amount

        portfolio_value = environment.cash_balance.amount + total_market_value
        return_percentage = (
            (total_unrealized_pnl / total_invested_amount * 100)
            if total_invested_amount > 0
            else Decimal("0")
        )

        return PortfolioPerformanceView(
            environment_id=environment_id,
            cash_balance=str(environment.cash_balance.amount),
            invested_amount=str(total_invested_amount),
            portfolio_value=str(portfolio_value),
            unrealized_pnl=str(total_unrealized_pnl),
            return_percentage=float(return_percentage),
        )
