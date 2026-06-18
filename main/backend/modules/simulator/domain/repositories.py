from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from backend.modules.simulator.domain.entities import Holding
from backend.modules.simulator.domain.entities import PortfolioSnapshot
from backend.modules.simulator.domain.entities import SimulatorEnvironment
from backend.modules.simulator.domain.entities import Transaction
from backend.shared.types import EnvironmentId
from backend.shared.types import HoldingId
from backend.shared.types import TransactionId


class EnvironmentRepository(ABC):
    """
    Repository contract for simulator environments.
    """

    @abstractmethod
    async def get(
        self,
        environment_id: EnvironmentId,
    ) -> SimulatorEnvironment | None:
        raise NotImplementedError

    @abstractmethod
    async def save(
        self,
        environment: SimulatorEnvironment,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete(
        self,
        environment_id: EnvironmentId,
    ) -> None:
        raise NotImplementedError


class HoldingRepository(ABC):
    """
    Repository contract for holdings.
    """

    @abstractmethod
    async def get(
        self,
        holding_id: HoldingId,
    ) -> Holding | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_environment(
        self,
        environment_id: EnvironmentId,
    ) -> list[Holding]:
        raise NotImplementedError

    @abstractmethod
    async def save(
        self,
        holding: Holding,
    ) -> None:
        raise NotImplementedError


class TransactionRepository(ABC):
    """
    Repository contract for transaction history.
    """

    @abstractmethod
    async def get(
        self,
        transaction_id: TransactionId,
    ) -> Transaction | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_environment(
        self,
        environment_id: EnvironmentId,
    ) -> list[Transaction]:
        raise NotImplementedError

    @abstractmethod
    async def save(
        self,
        transaction: Transaction,
    ) -> None:
        raise NotImplementedError


class PortfolioSnapshotRepository(ABC):
    """
    Repository contract for portfolio snapshots.

    Snapshots allow:
    - historical portfolio reconstruction
    - performance tracking
    - future backtesting
    - RL training datasets
    """

    @abstractmethod
    async def get_latest(
        self,
        environment_id: EnvironmentId,
    ) -> PortfolioSnapshot | None:
        raise NotImplementedError

    @abstractmethod
    async def save(
        self,
        snapshot: PortfolioSnapshot,
    ) -> None:
        raise NotImplementedError


# Purpose:
# Declares persistence contracts required by the simulator domain and application layers.
#
# Future Responsibilities:
# - Define how environments are loaded and saved.
# - Define how holdings and transactions are queried per environment.
# - Preserve environment isolation as a first-class repository concern.
#
# Dependencies:
# - backend.modules.simulator.domain.entities
#
# Future Classes / Interfaces:
# - EnvironmentRepository
# - HoldingRepository
# - TransactionRepository
# - PortfolioSnapshotRepository
#
# What Should Not Live Here:
# - SQLAlchemy models.
# - Query implementations.
# - API pagination response formatting.