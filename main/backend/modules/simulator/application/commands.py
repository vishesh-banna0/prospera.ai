from __future__ import annotations

import uuid
from datetime import UTC
from datetime import datetime
from decimal import Decimal

from backend.modules.market_data.application.services import MarketDataService
from backend.modules.market_data.application.dto import QuoteRequest
from backend.modules.simulator.application.dto import (
    CashAdjustmentInput,
    CreateEnvironmentInput,
    EnvironmentView,
    RenameEnvironmentInput,
    TradeOrderInput,
)
from backend.modules.simulator.domain.entities import (
    SimulatorEnvironment,
    Holding,
    Transaction,
)
from backend.modules.simulator.domain.policies import (
    can_buy,
    can_sell,
    calculate_cost_basis,
)
from backend.modules.simulator.domain.repositories import (
    EnvironmentRepository,
    HoldingRepository,
    TransactionRepository,
)
from backend.modules.simulator.domain.value_objects import ShareQuantity
from backend.shared.types import Money, TransactionType


class CreateEnvironmentUseCase:
    """Create a new isolated portfolio environment."""

    def __init__(
        self,
        environment_repository: EnvironmentRepository,
    ) -> None:
        self._environment_repository = environment_repository

    async def execute(
        self,
        request: CreateEnvironmentInput,
    ) -> EnvironmentView:
        environment = SimulatorEnvironment(
            environment_id=str(uuid.uuid4()),
            owner_type=request.owner_type,
            name=request.name,
            cash_balance=Money(amount=0, currency="USD"),
            created_at=datetime.now(UTC),
            is_active=True,
        )
        await self._environment_repository.save(environment)
        return EnvironmentView(
            environment_id=environment.environment_id,
            name=environment.name,
            owner_type=environment.owner_type,
            cash_balance=str(environment.cash_balance.amount),
            created_at=environment.created_at,
        )


class RenameEnvironmentUseCase:
    """Rename an existing environment."""

    def __init__(
        self,
        environment_repository: EnvironmentRepository,
    ) -> None:
        self._environment_repository = environment_repository

    async def execute(
        self,
        request: RenameEnvironmentInput,
    ) -> None:
        environment = await self._environment_repository.get(request.environment_id)
        if environment is None:
            raise ValueError(f"Environment {request.environment_id} not found")
        environment.name = request.new_name
        environment.updated_at = datetime.now(UTC)
        await self._environment_repository.save(environment)


class DeleteEnvironmentUseCase:
    """Delete an environment and all associated data."""

    def __init__(
        self,
        environment_repository: EnvironmentRepository,
    ) -> None:
        self._environment_repository = environment_repository

    async def execute(
        self,
        environment_id: str,
    ) -> None:
        await self._environment_repository.delete(environment_id)


class AddVirtualCashUseCase:
    """Deposit virtual cash into an environment."""

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
        environment = await self._environment_repository.get(request.environment_id)
        if environment is None:
            raise ValueError(f"Environment {request.environment_id} not found")
        environment.cash_balance = Money(
            amount=environment.cash_balance.amount + request.amount.amount,
            currency=environment.cash_balance.currency,
        )
        environment.updated_at = datetime.now(UTC)
        await self._environment_repository.save(environment)
        transaction = Transaction(
            transaction_id=str(uuid.uuid4()),
            environment_id=request.environment_id,
            transaction_type=TransactionType.DEPOSIT,
            amount=request.amount,
            executed_at=datetime.now(UTC),
        )
        await self._transaction_repository.save(transaction)


class WithdrawVirtualCashUseCase:
    """Withdraw virtual cash from an environment."""

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
        environment = await self._environment_repository.get(request.environment_id)
        if environment is None:
            raise ValueError(f"Environment {request.environment_id} not found")
        if environment.cash_balance < request.amount:
            raise ValueError("Insufficient cash balance")
        environment.cash_balance = Money(
            amount=environment.cash_balance.amount - request.amount.amount,
            currency=environment.cash_balance.currency,
        )
        environment.updated_at = datetime.now(UTC)
        await self._environment_repository.save(environment)
        transaction = Transaction(
            transaction_id=str(uuid.uuid4()),
            environment_id=request.environment_id,
            transaction_type=TransactionType.WITHDRAWAL,
            amount=request.amount,
            executed_at=datetime.now(UTC),
        )
        await self._transaction_repository.save(transaction)


class BuyStockUseCase:
    """Buy stocks in an environment."""

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
        environment = await self._environment_repository.get(request.environment_id)
        if environment is None:
            raise ValueError(f"Environment {request.environment_id} not found")

        quote = await self._market_data_service.get_quote(
            QuoteRequest(symbol=request.symbol)
        )
        price = Money(
            amount=Decimal(str(quote.last_price)),
            currency=quote.currency,
        )

        quantity = ShareQuantity(value=request.quantity)
        trade_cost = Money(
            amount=price.amount * quantity.value,
            currency=price.currency,
        )

        if not can_buy(environment.cash_balance, trade_cost):
            raise ValueError("Insufficient cash balance for this buy order")

        environment.cash_balance = Money(
            amount=environment.cash_balance.amount - trade_cost.amount,
            currency=environment.cash_balance.currency,
        )
        environment.updated_at = datetime.now(UTC)
        await self._environment_repository.save(environment)

        holdings = await self._holding_repository.list_by_environment(
            request.environment_id
        )
        holding = next(
            (h for h in holdings if h.symbol == request.symbol),
            None,
        )

        if holding is None:
            holding = Holding(
                holding_id=str(uuid.uuid4()),
                environment_id=request.environment_id,
                symbol=request.symbol,
                quantity=quantity,
                average_cost=price,
                created_at=datetime.now(UTC),
            )
        else:
            new_avg_cost = calculate_cost_basis(
                holding.quantity,
                holding.average_cost,
                quantity,
                price,
            )
            holding.quantity = ShareQuantity(
                value=holding.quantity.value + quantity.value
            )
            holding.average_cost = new_avg_cost
            holding.updated_at = datetime.now(UTC)

        await self._holding_repository.save(holding)

        transaction = Transaction(
            transaction_id=str(uuid.uuid4()),
            environment_id=request.environment_id,
            transaction_type=TransactionType.BUY,
            amount=trade_cost,
            symbol=request.symbol,
            quantity=quantity,
            executed_price=price,
            executed_at=datetime.now(UTC),
        )
        await self._transaction_repository.save(transaction)


class SellStockUseCase:
    """Sell stocks in an environment."""

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
        environment = await self._environment_repository.get(request.environment_id)
        if environment is None:
            raise ValueError(f"Environment {request.environment_id} not found")

        holdings = await self._holding_repository.list_by_environment(
            request.environment_id
        )
        holding = next(
            (h for h in holdings if h.symbol == request.symbol),
            None,
        )
        if holding is None:
            raise ValueError(f"No position in {request.symbol}")

        quantity = ShareQuantity(value=request.quantity)
        if not can_sell(holding, quantity):
            raise ValueError("Insufficient shares to sell")

        quote = await self._market_data_service.get_quote(
            QuoteRequest(symbol=request.symbol)
        )
        price = Money(
            amount=Decimal(str(quote.last_price)),
            currency=quote.currency,
        )

        proceeds = Money(
            amount=price.amount * quantity.value,
            currency=price.currency,
        )

        environment.cash_balance = Money(
            amount=environment.cash_balance.amount + proceeds.amount,
            currency=environment.cash_balance.currency,
        )
        environment.updated_at = datetime.now(UTC)
        await self._environment_repository.save(environment)

        new_quantity_value = holding.quantity.value - quantity.value
        if new_quantity_value > 0:
            holding.quantity = ShareQuantity(value=new_quantity_value)
            holding.updated_at = datetime.now(UTC)
            await self._holding_repository.save(holding)

        transaction = Transaction(
            transaction_id=str(uuid.uuid4()),
            environment_id=request.environment_id,
            transaction_type=TransactionType.SELL,
            amount=proceeds,
            symbol=request.symbol,
            quantity=quantity,
            executed_price=price,
            executed_at=datetime.now(UTC),
        )
        await self._transaction_repository.save(transaction)
