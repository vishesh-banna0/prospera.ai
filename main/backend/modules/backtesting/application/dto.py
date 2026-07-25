from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class LumpSumRequest:
    symbol: str
    amount: float
    start_at: datetime
    end_at: datetime
    # Index to compare against ("what if the same money went into the index").
    # None uses the app default (NIFTY 50); pass an empty string to disable.
    benchmark_symbol: str | None = None


@dataclass(frozen=True, slots=True)
class SipRequest:
    symbol: str
    monthly_amount: float
    start_at: datetime
    end_at: datetime
    benchmark_symbol: str | None = None


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
class BenchmarkComparisonView:
    """The same contribution schedule replayed against a benchmark index.

    Lets the caller answer "did this strategy beat the market?" — the benchmark
    runs the identical cash flows (same dates, same amounts) through the same
    engine, so the metrics are directly comparable. ``excess_*`` fields are the
    portfolio minus the benchmark.
    """

    symbol: str
    currency: str
    metrics: MetricsView
    excess_return_pct: float
    excess_cagr_pct: float
    outperformed: bool


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
    # Present when a benchmark was requested (default) and enough benchmark price
    # history was available; None when disabled or the benchmark could not load.
    benchmark: BenchmarkComparisonView | None = None


# Purpose:
# Application-layer request/response contracts for Phase 15 backtesting.
