from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.modules.simulator.domain.entities import (
    Holding,
    PortfolioSnapshot,
    SimulatorEnvironment,
    Transaction,
)
from backend.modules.simulator.domain.repositories import (
    EnvironmentRepository,
    HoldingRepository,
    PortfolioSnapshotRepository,
    TransactionRepository,
)
from backend.modules.simulator.domain.value_objects import ShareQuantity
from backend.modules.simulator.infrastructure.models import (
    EnvironmentModel,
    HoldingModel,
    PortfolioSnapshotModel,
    TransactionModel,
)
from backend.shared.types import (
    CurrencyCode,
    EnvironmentId,
    HoldingId,
    Money,
    OwnerType,
    TransactionId,
    TransactionType,
)


class SqlEnvironmentRepository(EnvironmentRepository):
    """SQL-based implementation of environment repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self,
        environment_id: EnvironmentId,
    ) -> SimulatorEnvironment | None:
        model = await self._get_model(environment_id)
        if model is None:
            return None

        return self._model_to_entity(model)

    async def save(
        self,
        environment: SimulatorEnvironment,
    ) -> None:
        model = await self._get_model(environment.environment_id)

        if model is None:
            self._session.add(
                EnvironmentModel(
                    environment_id=environment.environment_id,
                    owner_type=environment.owner_type.value,
                    name=environment.name,
                    cash_balance=environment.cash_balance.amount,
                    currency=str(environment.cash_balance.currency),
                    is_active=environment.is_active,
                    created_at=environment.created_at,
                    updated_at=environment.updated_at,
                )
            )
        else:
            model.owner_type = environment.owner_type.value
            model.name = environment.name
            model.cash_balance = environment.cash_balance.amount
            model.currency = str(environment.cash_balance.currency)
            model.is_active = environment.is_active
            model.updated_at = environment.updated_at

        await self._session.flush()

    async def delete(
        self,
        environment_id: EnvironmentId,
    ) -> None:
        model = await self._get_model(environment_id)
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()

    async def _get_model(
        self,
        environment_id: EnvironmentId,
    ) -> EnvironmentModel | None:
        stmt = select(EnvironmentModel).where(
            EnvironmentModel.environment_id == environment_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def _model_to_entity(model: EnvironmentModel) -> SimulatorEnvironment:
        return SimulatorEnvironment(
            environment_id=model.environment_id,
            owner_type=OwnerType(model.owner_type),
            name=model.name,
            cash_balance=Money(
                amount=model.cash_balance,
                currency=CurrencyCode(model.currency),
            ),
            created_at=model.created_at,
            updated_at=model.updated_at,
            is_active=model.is_active,
        )


class SqlHoldingRepository(HoldingRepository):
    """SQL-based implementation of holding repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self,
        holding_id: HoldingId,
    ) -> Holding | None:
        stmt = select(HoldingModel).where(
            HoldingModel.holding_id == holding_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._model_to_entity(model)

    async def list_by_environment(
        self,
        environment_id: EnvironmentId,
    ) -> list[Holding]:
        stmt = select(HoldingModel).where(
            HoldingModel.environment_id == environment_id
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def save(
        self,
        holding: Holding,
    ) -> None:
        stmt = select(HoldingModel).where(
            HoldingModel.holding_id == holding.holding_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            self._session.add(
                HoldingModel(
                    holding_id=holding.holding_id,
                    environment_id=holding.environment_id,
                    symbol=holding.symbol,
                    quantity=holding.quantity.value,
                    average_cost=holding.average_cost.amount,
                    currency=str(holding.average_cost.currency),
                    created_at=holding.created_at,
                    updated_at=holding.updated_at,
                )
            )
        else:
            model.quantity = holding.quantity.value
            model.average_cost = holding.average_cost.amount
            model.currency = str(holding.average_cost.currency)
            model.updated_at = holding.updated_at

        await self._session.flush()

    @staticmethod
    def _model_to_entity(model: HoldingModel) -> Holding:
        return Holding(
            holding_id=model.holding_id,
            environment_id=model.environment_id,
            symbol=model.symbol,
            quantity=ShareQuantity(value=model.quantity),
            average_cost=Money(
                amount=model.average_cost,
                currency=CurrencyCode(model.currency),
            ),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SqlTransactionRepository(TransactionRepository):
    """SQL-based implementation of transaction repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self,
        transaction_id: TransactionId,
    ) -> Transaction | None:
        stmt = select(TransactionModel).where(
            TransactionModel.transaction_id == transaction_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._model_to_entity(model)

    async def list_by_environment(
        self,
        environment_id: EnvironmentId,
    ) -> list[Transaction]:
        stmt = (
            select(TransactionModel)
            .where(TransactionModel.environment_id == environment_id)
            .order_by(TransactionModel.executed_at.desc())
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def save(
        self,
        transaction: Transaction,
    ) -> None:
        currency = (
            transaction.executed_price.currency
            if transaction.executed_price is not None
            else transaction.amount.currency
        )
        self._session.add(
            TransactionModel(
                transaction_id=transaction.transaction_id,
                environment_id=transaction.environment_id,
                transaction_type=transaction.transaction_type.value,
                symbol=transaction.symbol,
                quantity=(
                    transaction.quantity.value
                    if transaction.quantity is not None
                    else None
                ),
                executed_price=(
                    transaction.executed_price.amount
                    if transaction.executed_price is not None
                    else None
                ),
                amount=transaction.amount.amount,
                currency=str(currency),
                notes=transaction.notes,
                executed_at=transaction.executed_at,
            )
        )
        await self._session.flush()

    @staticmethod
    def _model_to_entity(model: TransactionModel) -> Transaction:
        return Transaction(
            transaction_id=model.transaction_id,
            environment_id=model.environment_id,
            transaction_type=TransactionType(model.transaction_type),
            amount=Money(
                amount=model.amount,
                currency=CurrencyCode(model.currency),
            ),
            executed_at=model.executed_at,
            symbol=model.symbol,
            quantity=(
                ShareQuantity(value=model.quantity)
                if model.quantity is not None
                else None
            ),
            executed_price=(
                Money(
                    amount=model.executed_price,
                    currency=CurrencyCode(model.currency),
                )
                if model.executed_price is not None
                else None
            ),
            notes=model.notes,
        )


class SqlPortfolioSnapshotRepository(PortfolioSnapshotRepository):
    """SQL-based implementation of portfolio snapshot repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_latest(
        self,
        environment_id: EnvironmentId,
    ) -> PortfolioSnapshot | None:
        stmt = (
            select(PortfolioSnapshotModel)
            .where(PortfolioSnapshotModel.environment_id == environment_id)
            .order_by(PortfolioSnapshotModel.snapshot_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._model_to_entity(model)

    async def save(
        self,
        snapshot: PortfolioSnapshot,
    ) -> None:
        self._session.add(
            PortfolioSnapshotModel(
                environment_id=snapshot.environment_id,
                snapshot_at=snapshot.snapshot_at,
                cash_balance=snapshot.cash_balance.amount,
                portfolio_value=snapshot.portfolio_value.amount,
                total_value=snapshot.total_value.amount,
                unrealized_pnl=snapshot.unrealized_pnl.amount,
                currency=str(snapshot.cash_balance.currency),
            )
        )
        await self._session.flush()

    @staticmethod
    def _model_to_entity(model: PortfolioSnapshotModel) -> PortfolioSnapshot:
        currency = CurrencyCode(model.currency)
        return PortfolioSnapshot(
            environment_id=model.environment_id,
            snapshot_at=model.snapshot_at,
            cash_balance=Money(amount=model.cash_balance, currency=currency),
            portfolio_value=Money(amount=model.portfolio_value, currency=currency),
            total_value=Money(amount=model.total_value, currency=currency),
            unrealized_pnl=Money(amount=model.unrealized_pnl, currency=currency),
        )


"""
Purpose:
Implement environment, holding, transaction, and portfolio snapshot repository contracts.
Translate persistence models to and from domain entities.
Keep transactional write concerns isolated from the application layer.

Dependencies:
- backend.modules.simulator.domain.repositories (abstract contracts)
- backend.modules.simulator.infrastructure.models (SQLAlchemy ORM models)
- SQLAlchemy async session management

Classes:
- SqlEnvironmentRepository: Manages environment persistence
- SqlHoldingRepository: Manages stock holdings
- SqlTransactionRepository: Manages transaction history
- SqlPortfolioSnapshotRepository: Manages portfolio snapshots

What Should Not Live Here:
- Route authorization
- HTTP error handling
- Market pricing logic
"""
