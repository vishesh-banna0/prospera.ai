from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class LumpSumRequest:
    symbol: str
    amount: float
    start_at: datetime
    end_at: datetime


@dataclass(frozen=True, slots=True)
class SipRequest:
    symbol: str
    monthly_amount: float
    start_at: datetime
    end_at: datetime


@dataclass(frozen=True, slots=True)
class MetricsView:
    total_invested: float
    final_value: float
    profit: float
    total_return_pct: float
    cagr_pct: float
    xirr_pct: float
    annualized_volatility_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float


@dataclass(frozen=True, slots=True)
class EquityPointView:
    on: date
    invested: float
    value: float


@dataclass(frozen=True, slots=True)
class BacktestResultView:
    symbol: str
    strategy: str
    currency: str
    start_date: date
    end_date: date
    units: float
    metrics: MetricsView
    curve: tuple[EquityPointView, ...] = field(default_factory=tuple)


# Purpose:
# Application-layer request/response contracts for Phase 15 backtesting.
