from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field

from backend.modules.simulator.domain.value_objects import (
    AverageCostBasis,
    ShareQuantity,
)
from backend.shared.types import (
    EnvironmentId,
    HoldingId,
    Money,
    OwnerType,
    Symbol,
    Timestamp,
    TransactionId,
    TransactionType,
)


@dataclass(slots=True)
class SimulatorEnvironment:
    """
    Represents an isolated portfolio environment.

    Examples:
    - User portfolio
    - AI-managed portfolio
    - RL training portfolio
    - Backtesting portfolio
    """

    environment_id: EnvironmentId
    owner_type: OwnerType

    name: str

    cash_balance: Money

    created_at: Timestamp
    updated_at: Timestamp | None = None

    is_active: bool = True


@dataclass(slots=True)
class Holding:
    """
    Represents a position currently owned
    inside an environment.
    """

    holding_id: HoldingId

    environment_id: EnvironmentId

    symbol: Symbol

    quantity: ShareQuantity

    average_cost: AverageCostBasis

    created_at: Timestamp
    updated_at: Timestamp | None = None


@dataclass(slots=True)
class Transaction:
    """
    Immutable transaction record.

    Used for:
    - audit history
    - performance calculations
    - historical reconstruction
    - future backtesting
    """

    transaction_id: TransactionId

    environment_id: EnvironmentId

    transaction_type: TransactionType

    amount: Money

    executed_at: Timestamp

    symbol: Symbol | None = None

    quantity: ShareQuantity | None = None

    executed_price: Money | None = None

    notes: str | None = None


@dataclass(slots=True)
class PortfolioSnapshot:
    """
    Periodic valuation snapshot.

    Useful for:
    - performance charts
    - historical portfolio tracking
    - RL datasets
    - analytics
    """

    environment_id: EnvironmentId

    snapshot_at: Timestamp

    cash_balance: Money

    portfolio_value: Money

    total_value: Money

    unrealized_pnl: Money = field(
        default_factory=lambda: Money(amount=0)
    )
# Purpose:
# Placeholder definitions for simulator domain entities.
#
# Future Responsibilities:
# - Represent isolated environments such as user, AI, RL, and backtesting portfolios.
# - Represent holdings owned inside one environment.
# - Represent transaction history used for auditability and performance analysis.
# - Represent portfolio snapshots if periodic valuation is introduced later.
#
# Dependencies:
# - backend.shared.types
# - backend.modules.simulator.domain.value_objects
#
# Future Classes:
# - SimulatorEnvironment
# - Holding
# - Transaction
# - PortfolioSnapshot
#
# Future Fields:
# - environment_id
# - owner_type
# - name
# - cash_balance
# - symbol
# - quantity
# - average_cost
# - transaction_type
# - executed_price
# - executed_at
#
# What Should Not Live Here:
# - ORM mappings.
# - HTTP serialization concerns.
# - External price fetching behavior.
