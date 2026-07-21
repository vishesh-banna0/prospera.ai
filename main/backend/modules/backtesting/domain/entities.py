from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum


class Strategy(StrEnum):
    LUMP_SUM = "lump_sum"
    SIP = "sip"  # Systematic Investment Plan (periodic contributions)


@dataclass(frozen=True, slots=True)
class BacktestMetrics:
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
class EquityPoint:
    on: date
    invested: float
    value: float


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """The outcome of replaying one investment strategy over historical prices."""

    symbol: str
    strategy: Strategy
    currency: str
    start_date: date
    end_date: date
    units: float
    metrics: BacktestMetrics
    curve: tuple[EquityPoint, ...] = field(default_factory=tuple)


# Purpose:
# Types describing a historical investment simulation and its analytics.
#
# What Should Not Live Here:
# - The simulation math (engine.py) or metric formulas (metrics.py).
# - Price fetching (application service) or persistence.
