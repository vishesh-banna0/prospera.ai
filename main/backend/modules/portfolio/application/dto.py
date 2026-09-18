from __future__ import annotations

from dataclasses import dataclass, field


# ============================================================
# Inputs
# ============================================================


@dataclass(frozen=True, slots=True)
class OptimizePortfolioRequest:
    """Ask for target weights over a set of assets.

    Supply either ``symbols`` (optimize an arbitrary candidate basket) or
    ``environment_id`` (optimize what the portfolio actually holds, and get
    rebalancing trades back). Supplying both optimizes the given symbols and
    still diffs the result against the environment's holdings.
    """

    symbols: tuple[str, ...] = ()
    environment_id: str | None = None
    objective: str = "max_sharpe"
    lookback_days: int = 365
    risk_free_rate: float = 0.0
    # Cap on any single position. The standard guard against an optimizer
    # concentrating everything into whichever estimate it happens to like.
    max_weight: float = 0.35


@dataclass(frozen=True, slots=True)
class PortfolioRiskRequest:
    """Analyze the risk of an environment's current holdings as they stand."""

    environment_id: str
    lookback_days: int = 365
    risk_free_rate: float = 0.0


# ============================================================
# Views
# ============================================================


@dataclass(frozen=True, slots=True)
class AllocationView:
    symbol: str
    target_weight_pct: float
    # Present when the request was tied to an environment with holdings.
    current_weight_pct: float | None = None
    weight_change_pct: float | None = None
    # Share of total portfolio risk, which is not the same as capital weight.
    risk_contribution_pct: float = 0.0
    annualized_return_pct: float = 0.0
    annualized_volatility_pct: float = 0.0


@dataclass(frozen=True, slots=True)
class RebalanceTradeView:
    symbol: str
    action: str  # "buy" | "sell"
    amount: str  # currency amount, as a string to avoid float money
    reason: str


@dataclass(frozen=True, slots=True)
class PortfolioMetricsView:
    expected_return_pct: float
    volatility_pct: float
    sharpe_ratio: float
    diversification_ratio: float
    effective_number_of_assets: float
    max_drawdown_pct: float
    historical_return_pct: float


@dataclass(frozen=True, slots=True)
class CorrelationRowView:
    symbol: str
    correlations: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class PortfolioOptimizationView:
    objective: str
    symbols: tuple[str, ...]
    allocations: tuple[AllocationView, ...]
    optimized: PortfolioMetricsView
    # Equal weight is the honest baseline: an optimizer that cannot beat it is
    # not earning its complexity, so it is always reported alongside.
    equal_weight_baseline: PortfolioMetricsView
    correlations: tuple[CorrelationRowView, ...] = ()
    trades: tuple[RebalanceTradeView, ...] = ()
    observations: int = 0
    lookback_days: int = 0
    currency: str = "INR"
    notes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class PortfolioRiskView:
    environment_id: str
    symbols: tuple[str, ...]
    allocations: tuple[AllocationView, ...]
    metrics: PortfolioMetricsView
    correlations: tuple[CorrelationRowView, ...] = ()
    concentration_warnings: tuple[str, ...] = ()
    observations: int = 0
    currency: str = "INR"
