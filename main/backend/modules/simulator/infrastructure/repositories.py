from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.modules.simulator.domain.entities import (
    Environment,
    Holding,
    PortfolioSnapshot,
    Transaction,
)
from backend.modules.simulator.domain.repositories import (
    EnvironmentRepository,
    HoldingRepository,
    PortfolioSnapshotRepository,
    TransactionRepository,
)
from backend.modules.simulator.infrastructure.models import (
    EnvironmentModel,
    HoldingModel,
    PortfolioSnapshotModel,
    TransactionModel,
)
from backend.shared.types import (
    EnvironmentId,
    HoldingId,
    PortfolioSnapshotId,
    TransactionId,
)


class SqlEnvironmentRepository(EnvironmentRepository):
    """SQL-based implementation of environment repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self,
        environment_id: EnvironmentId,
    ) -> Environment | None:
        stmt = select(EnvironmentModel).where(
            EnvironmentModel.environment_id == environment_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._model_to_entity(model)

    async def save(
        self,
        environment: Environment,
    ) -> None:
        model = EnvironmentModel(
            environment_id=environment.environment_id,
            owner_type=environment.owner_type,
            name=environment.name,
            cash_balance=environment.cash_balance,
            is_active=environment.is_active,
        )
        self._session.add(model)
        await self._session.flush()

    async def delete(
        self,
        environment_id: EnvironmentId,
    ) -> None:
        stmt = select(EnvironmentModel).where(
            EnvironmentModel.environment_id == environment_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is not None:
            await self._session.delete(model)
            await self._session.flush()

    @staticmethod
    def _model_to_entity(model: EnvironmentModel) -> Environment:
        return Environment(
            environment_id=model.environment_id,
            owner_type=model.owner_type,
            name=model.name,
            cash_balance=model.cash_balance,
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
        model = HoldingModel(
            holding_id=holding.holding_id,
            environment_id=holding.environment_id,
            symbol=holding.symbol,
            quantity=holding.quantity,
            cost_basis=holding.cost_basis,
        )
        self._session.add(model)
        await self._session.flush()

    @staticmethod
    def _model_to_entity(model: HoldingModel) -> Holding:
        return Holding(
            holding_id=model.holding_id,
            environment_id=model.environment_id,
            symbol=model.symbol,
            quantity=model.quantity,
            cost_basis=model.cost_basis,
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
        stmt = select(TransactionModel).where(
            TransactionModel.environment_id == environment_id
        ).order_by(TransactionModel.transaction_date.desc())
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def save(
        self,
        transaction: Transaction,
    ) -> None:
        model = TransactionModel(
            transaction_id=transaction.transaction_id,
            environment_id=transaction.environment_id,
            symbol=transaction.symbol,
            side=transaction.side.value,
            quantity=transaction.quantity,
            price=transaction.price,
            transaction_date=transaction.transaction_date,
        )
        self._session.add(model)
        await self._session.flush()

    @staticmethod
    def _model_to_entity(model: TransactionModel) -> Transaction:
        from backend.modules.simulator.domain.value_objects import (
            TransactionSide,
        )

        return Transaction(
            transaction_id=model.transaction_id,
            environment_id=model.environment_id,
            symbol=model.symbol,
            side=TransactionSide(model.side),
            quantity=model.quantity,
            price=model.price,
            transaction_date=model.transaction_date,
        )


class SqlPortfolioSnapshotRepository(PortfolioSnapshotRepository):
    """SQL-based implementation of portfolio snapshot repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self,
        snapshot_id: PortfolioSnapshotId,
    ) -> PortfolioSnapshot | None:
        stmt = select(PortfolioSnapshotModel).where(
            PortfolioSnapshotModel.snapshot_id == snapshot_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._model_to_entity(model)

    async def list_by_environment(
        self,
        environment_id: EnvironmentId,
    ) -> list[PortfolioSnapshot]:
        stmt = select(PortfolioSnapshotModel).where(
            PortfolioSnapshotModel.environment_id == environment_id
        ).order_by(PortfolioSnapshotModel.snapshot_date.desc())
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def save(
        self,
        snapshot: PortfolioSnapshot,
    ) -> None:
        model = PortfolioSnapshotModel(
            snapshot_id=snapshot.snapshot_id,
            environment_id=snapshot.environment_id,
            total_value=snapshot.total_value,
            cash_balance=snapshot.cash_balance,
            market_value=snapshot.market_value,
            snapshot_date=snapshot.snapshot_date,
        )
        self._session.add(model)
        await self._session.flush()

    @staticmethod
    def _model_to_entity(model: PortfolioSnapshotModel) -> PortfolioSnapshot:
        return PortfolioSnapshot(
            snapshot_id=model.snapshot_id,
            environment_id=model.environment_id,
            total_value=model.total_value,
            cash_balance=model.cash_balance,
            market_value=model.market_value,
            snapshot_date=model.snapshot_date,
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
