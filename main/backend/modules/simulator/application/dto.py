from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from backend.modules.simulator.domain.sip import SipFrequency
from backend.shared.types import (
    EnvironmentId,
    Money,
    OwnerType,
    Symbol,
    Timestamp,
    TransactionId,
    TransactionType,
)


# ============================================================
# Inputs
# ============================================================


@dataclass(frozen=True, slots=True)
class CreateEnvironmentInput:
    name: str
    owner_type: OwnerType


@dataclass(frozen=True, slots=True)
class RenameEnvironmentInput:
    environment_id: EnvironmentId
    new_name: str


@dataclass(frozen=True, slots=True)
class CashAdjustmentInput:
    environment_id: EnvironmentId
    amount: Money


@dataclass(frozen=True, slots=True)
class TradeOrderInput:
    environment_id: EnvironmentId
    symbol: Symbol
    quantity: float
    order_type: TransactionType


@dataclass(frozen=True, slots=True)
class CreateSipPlanInput:
    environment_id: EnvironmentId
    symbol: Symbol
    amount: Money
    frequency: SipFrequency = SipFrequency.MONTHLY
    start_date: date | None = None
    end_date: date | None = None
    name: str | None = None


# ============================================================
# Views
# ============================================================


@dataclass(frozen=True, slots=True)
class EnvironmentView:
    environment_id: EnvironmentId
    name: str
    owner_type: OwnerType
    cash_balance: str
    created_at: Timestamp


@dataclass(frozen=True, slots=True)
class HoldingView:
    symbol: Symbol
    quantity: float

    average_cost: str

    market_value: str | None = None

    unrealized_pnl: str | None = None

    return_percentage: float | None = None


@dataclass(frozen=True, slots=True)
class TransactionView:
    transaction_id: TransactionId

    symbol: Symbol | None

    transaction_type: TransactionType

    quantity: float | None

    amount: str

    executed_at: Timestamp


@dataclass(frozen=True, slots=True)
class PortfolioPerformanceView:
    environment_id: EnvironmentId

    cash_balance: str

    invested_amount: str

    portfolio_value: str

    unrealized_pnl: str

    return_percentage: float


@dataclass(frozen=True, slots=True)
class PortfolioView:
    environment_id: EnvironmentId

    holdings: tuple[HoldingView, ...]

    performance: PortfolioPerformanceView


@dataclass(frozen=True, slots=True)
class SipPlanView:
    plan_id: str

    environment_id: EnvironmentId

    symbol: Symbol

    symbol_name: str | None

    amount: str

    frequency: str

    day_of_month: int

    start_date: date

    next_run_date: date

    end_date: date | None

    status: str

    installments_run: int

    installments_skipped: int

    last_run_at: Timestamp | None

    created_at: Timestamp | None
# Purpose:
# Defines application-layer request and response contracts for simulator workflows.
#
# Future Responsibilities:
# - Standardize input structures for environment, cash, and trade use cases.
# - Standardize output structures for holdings, transactions, and performance views.
# - Keep the API layer and future agent interfaces decoupled from domain internals.
#
# Dependencies:
# - backend.shared.types
#
# Future Classes:
# - CreateEnvironmentInput
# - RenameEnvironmentInput
# - CashAdjustmentInput
# - TradeOrderInput
# - HoldingView
# - TransactionView
# - PortfolioPerformanceView
#
# What Should Not Live Here:
# - Business rule execution.
# - Database mapping logic.
# - HTTP status code concerns.
