from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import numpy as np
import pytest

from backend.modules.portfolio.application.dto import (
    OptimizePortfolioRequest,
    PortfolioRiskRequest,
)
from backend.modules.portfolio.application.services import (
    PortfolioOptimizationService,
)
from backend.modules.portfolio.domain import risk as risk_analytics
from backend.modules.portfolio.domain.optimizer import (
    Objective,
    annualized_moments,
    daily_returns_matrix,
    optimize_weights,
)


# ---------------------------------------------------------------------------
# Synthetic price generators — deterministic, no network, no randomness that
# would make an assertion flaky.
# ---------------------------------------------------------------------------


def _series(
    n: int,
    drift: float,
    amplitude: float,
    period: int,
    phase: float = 0.0,
    start: float = 100.0,
) -> list[float]:
    """A smooth, reproducible price path: exponential drift + a sine wave.

    The sine term supplies volatility whose phase we control, which is what
    lets a test create two assets that are genuinely uncorrelated (quarter-
    period offset) or perfectly correlated (same phase).
    """
    return [
        start
        * math.exp(drift * i / 252.0)
        * (1.0 + amplitude * math.sin(2.0 * math.pi * i / period + phase))
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Domain: optimizer
# ---------------------------------------------------------------------------


def test_returns_matrix_aligns_series_to_the_shortest_history() -> None:
    symbols, returns = daily_returns_matrix(
        {
            "LONG": _series(300, 0.10, 0.02, 40),
            "SHORT": _series(120, 0.10, 0.02, 40),
            "TOO_SHORT": [100.0],  # dropped: a single price yields no return
        }
    )

    assert symbols == ("LONG", "SHORT")
    # Truncated to the shorter history (120 prices -> 119 returns).
    assert returns.shape == (119, 2)


def test_weights_are_long_only_fully_invested_and_capped() -> None:
    _, returns = daily_returns_matrix(
        {
            "A": _series(400, 0.20, 0.010, 30),
            "B": _series(400, 0.05, 0.030, 45, phase=1.1),
            "C": _series(400, 0.12, 0.020, 60, phase=2.3),
        }
    )
    mean, cov = annualized_moments(returns)

    for objective in Objective:
        weights = optimize_weights(objective, mean, cov, max_weight=0.5)

        assert weights.shape == (3,)
        assert np.all(weights >= -1e-9), f"{objective} produced a short position"
        assert weights.sum() == pytest.approx(1.0, abs=1e-6), f"{objective} not invested"
        assert weights.max() <= 0.5 + 1e-6, f"{objective} breached the weight cap"


def test_min_variance_beats_equal_weight_on_volatility() -> None:
    """The defining property: if it doesn't lower variance, it isn't working."""
    _, returns = daily_returns_matrix(
        {
            "CALM": _series(500, 0.08, 0.005, 30),
            "WILD": _series(500, 0.08, 0.060, 30, phase=0.4),
            "MID": _series(500, 0.08, 0.020, 50, phase=2.0),
        }
    )
    mean, cov = annualized_moments(returns)

    min_var = optimize_weights(Objective.MIN_VARIANCE, mean, cov, max_weight=1.0)
    equal = np.full(3, 1.0 / 3.0)

    assert risk_analytics.portfolio_volatility(
        min_var, cov
    ) < risk_analytics.portfolio_volatility(equal, cov)
    # It should lean toward the calm asset.
    assert min_var[0] > min_var[1]


def test_max_sharpe_beats_equal_weight_on_sharpe() -> None:
    _, returns = daily_returns_matrix(
        {
            "GOOD": _series(500, 0.25, 0.010, 30),  # high drift, low vol
            "POOR": _series(500, 0.02, 0.050, 35, phase=1.5),  # low drift, high vol
        }
    )
    mean, cov = annualized_moments(returns)

    max_sharpe = optimize_weights(Objective.MAX_SHARPE, mean, cov, max_weight=1.0)
    equal = np.full(2, 0.5)

    assert risk_analytics.sharpe_ratio(
        max_sharpe, mean, cov
    ) >= risk_analytics.sharpe_ratio(equal, mean, cov)
    assert max_sharpe[0] > max_sharpe[1]  # favours the better reward-per-risk asset


def test_inverse_volatility_underweights_the_volatile_asset() -> None:
    symbols, returns = daily_returns_matrix(
        {
            "CALM": _series(400, 0.10, 0.004, 30),
            "WILD": _series(400, 0.10, 0.040, 30, phase=0.7),
        }
    )
    mean, cov = annualized_moments(returns)

    weights = optimize_weights(Objective.INVERSE_VOLATILITY, mean, cov, max_weight=1.0)

    assert symbols == ("CALM", "WILD")
    assert weights[0] > weights[1]


def test_single_asset_and_empty_inputs_are_handled() -> None:
    _, returns = daily_returns_matrix({"ONLY": _series(200, 0.10, 0.02, 30)})
    mean, cov = annualized_moments(returns)

    assert optimize_weights(Objective.MAX_SHARPE, mean, cov) == pytest.approx([1.0])

    empty_symbols, empty_returns = daily_returns_matrix({})
    assert empty_symbols == ()
    assert empty_returns.size == 0


def test_unsatisfiable_weight_cap_falls_back_to_equal_weight() -> None:
    """cap * n < 1 cannot sum to 1; equal weight is the only sane answer."""
    _, returns = daily_returns_matrix(
        {
            "A": _series(300, 0.10, 0.02, 30),
            "B": _series(300, 0.08, 0.03, 40, phase=1.0),
        }
    )
    mean, cov = annualized_moments(returns)

    weights = optimize_weights(Objective.MIN_VARIANCE, mean, cov, max_weight=0.1)

    assert weights == pytest.approx([0.5, 0.5])


# ---------------------------------------------------------------------------
# Domain: risk analytics
# ---------------------------------------------------------------------------


def test_risk_contributions_sum_to_one_and_exceed_capital_weight() -> None:
    _, returns = daily_returns_matrix(
        {
            "CALM": _series(400, 0.10, 0.005, 30),
            "WILD": _series(400, 0.10, 0.050, 30, phase=0.9),
        }
    )
    _, cov = annualized_moments(returns)
    weights = np.array([0.5, 0.5])

    contributions = risk_analytics.risk_contributions(weights, cov)

    assert contributions.sum() == pytest.approx(1.0, abs=1e-9)
    # Equal capital, unequal risk — the whole point of the measure.
    assert contributions[1] > 0.5 > contributions[0]


def test_diversification_ratio_is_one_for_identical_assets() -> None:
    path = _series(400, 0.10, 0.02, 30)
    _, returns = daily_returns_matrix({"A": path, "B": list(path)})
    _, cov = annualized_moments(returns, covariance_shrinkage=0.0)

    ratio = risk_analytics.diversification_ratio(np.array([0.5, 0.5]), cov)

    # Perfectly correlated holdings buy no diversification.
    assert ratio == pytest.approx(1.0, abs=1e-3)


def test_effective_number_of_assets_detects_concentration() -> None:
    assert risk_analytics.effective_number_of_assets(
        np.array([0.25, 0.25, 0.25, 0.25])
    ) == pytest.approx(4.0)
    # Four names, but one is 91% of capital.
    assert (
        risk_analytics.effective_number_of_assets(np.array([0.91, 0.03, 0.03, 0.03]))
        < 1.3
    )


def test_historical_performance_reports_drawdown() -> None:
    # Straight up then straight down: a 50% peak-to-trough decline.
    prices = [100.0, 200.0, 100.0]
    _, returns = daily_returns_matrix({"X": prices})

    total_return_pct, max_drawdown_pct = risk_analytics.historical_performance(
        returns, np.array([1.0])
    )

    assert total_return_pct == pytest.approx(0.0, abs=1e-6)
    assert max_drawdown_pct == pytest.approx(50.0, abs=1e-6)


# ---------------------------------------------------------------------------
# Application service — with fakes standing in for market data + holdings
# ---------------------------------------------------------------------------


@dataclass
class _FakePricePoint:
    timestamp: datetime
    close_price: str


@dataclass
class _FakeSeriesView:
    symbol: str
    currency: str
    prices: tuple[_FakePricePoint, ...]


class _FakeMarketData:
    """Serves canned price history; raises for symbols it doesn't know."""

    def __init__(self, series_by_symbol: dict[str, list[float]]) -> None:
        self._series = series_by_symbol

    async def get_historical_prices(self, request) -> _FakeSeriesView:
        symbol = request.symbol.upper()
        if symbol not in self._series:
            raise ValueError(f"no history for {symbol}")
        start = datetime.now(UTC) - timedelta(days=len(self._series[symbol]))
        return _FakeSeriesView(
            symbol=symbol,
            currency="INR",
            prices=tuple(
                _FakePricePoint(
                    timestamp=start + timedelta(days=i),
                    close_price=str(price),
                )
                for i, price in enumerate(self._series[symbol])
            ),
        )


class _FakeQuantity:
    def __init__(self, value: float) -> None:
        self.value = value


class _FakeCost:
    def __init__(self, amount: str) -> None:
        self.amount = Decimal(amount)


class _FakeHolding:
    def __init__(self, symbol: str, quantity: float, average_cost: str) -> None:
        self.symbol = symbol
        self.quantity = _FakeQuantity(quantity)
        self.average_cost = _FakeCost(average_cost)


class _FakeHoldingRepository:
    def __init__(self, holdings: list[_FakeHolding]) -> None:
        self._holdings = holdings

    async def list_by_environment(self, environment_id):
        return self._holdings


def _service(
    series: dict[str, list[float]],
    holdings: list[_FakeHolding] | None = None,
) -> PortfolioOptimizationService:
    return PortfolioOptimizationService(
        market_data_service=_FakeMarketData(series),
        holding_repository=(
            _FakeHoldingRepository(holdings) if holdings is not None else None
        ),
    )


@pytest.mark.asyncio
async def test_optimize_returns_weights_metrics_and_baseline() -> None:
    service = _service(
        {
            "AAA": _series(400, 0.20, 0.010, 30),
            "BBB": _series(400, 0.06, 0.035, 45, phase=1.2),
            "CCC": _series(400, 0.12, 0.020, 60, phase=2.5),
        }
    )

    result = await service.optimize(
        OptimizePortfolioRequest(
            symbols=("AAA", "BBB", "CCC"),
            objective="max_sharpe",
            max_weight=0.6,
        )
    )

    assert result.objective == "max_sharpe"
    assert result.symbols == ("AAA", "BBB", "CCC")
    assert len(result.allocations) == 3
    assert sum(a.target_weight_pct for a in result.allocations) == pytest.approx(
        100.0, abs=0.1
    )
    assert all(a.target_weight_pct <= 60.0 + 1e-6 for a in result.allocations)
    # Allocations arrive sorted by weight, largest first.
    weights = [a.target_weight_pct for a in result.allocations]
    assert weights == sorted(weights, reverse=True)
    # The equal-weight baseline is always reported for comparison.
    assert result.equal_weight_baseline.volatility_pct > 0
    assert result.optimized.sharpe_ratio >= result.equal_weight_baseline.sharpe_ratio
    # Correlation matrix is square and has a unit diagonal.
    assert len(result.correlations) == 3
    for i, row in enumerate(result.correlations):
        assert len(row.correlations) == 3
        assert row.correlations[i] == pytest.approx(1.0, abs=1e-6)
    assert result.observations > 0
    assert result.currency == "INR"


@pytest.mark.asyncio
async def test_optimize_skips_symbols_without_history_and_says_so() -> None:
    service = _service(
        {
            "AAA": _series(300, 0.15, 0.015, 30),
            "BBB": _series(300, 0.08, 0.025, 40, phase=1.0),
        }
    )

    result = await service.optimize(
        OptimizePortfolioRequest(symbols=("AAA", "BBB", "DELISTED"))
    )

    assert result.symbols == ("AAA", "BBB")
    assert any("DELISTED" in note for note in result.notes)


@pytest.mark.asyncio
async def test_optimize_from_holdings_produces_rebalancing_trades() -> None:
    holdings = [
        # Deliberately lopsided: 90% of capital in one name.
        _FakeHolding("AAA", quantity=900.0, average_cost="100.00"),
        _FakeHolding("BBB", quantity=100.0, average_cost="100.00"),
    ]
    service = _service(
        {
            "AAA": _series(400, 0.10, 0.040, 30),
            "BBB": _series(400, 0.10, 0.010, 45, phase=1.3),
        },
        holdings=holdings,
    )

    result = await service.optimize(
        OptimizePortfolioRequest(
            environment_id="env-1",
            objective="min_variance",
            max_weight=1.0,
        )
    )

    by_symbol = {a.symbol: a for a in result.allocations}
    assert by_symbol["AAA"].current_weight_pct == pytest.approx(90.0, abs=0.1)
    assert by_symbol["BBB"].current_weight_pct == pytest.approx(10.0, abs=0.1)
    # Min-variance should cut the volatile, over-weighted position.
    assert by_symbol["AAA"].weight_change_pct < 0

    actions = {t.symbol: t.action for t in result.trades}
    assert actions["AAA"] == "sell"
    assert actions["BBB"] == "buy"
    assert all(float(t.amount) > 0 for t in result.trades)


@pytest.mark.asyncio
async def test_analyze_holdings_flags_concentration() -> None:
    holdings = [
        _FakeHolding("AAA", quantity=950.0, average_cost="100.00"),
        _FakeHolding("BBB", quantity=50.0, average_cost="100.00"),
    ]
    service = _service(
        {
            "AAA": _series(400, 0.10, 0.040, 30),
            "BBB": _series(400, 0.10, 0.010, 45, phase=1.3),
        },
        holdings=holdings,
    )

    result = await service.analyze_holdings(PortfolioRiskRequest(environment_id="env-1"))

    assert result.environment_id == "env-1"
    assert result.metrics.volatility_pct > 0
    assert sum(a.risk_contribution_pct for a in result.allocations) == pytest.approx(
        100.0, abs=0.5
    )
    # 95% in one name must be called out, on capital and on risk.
    assert any("AAA" in warning for warning in result.concentration_warnings)
    assert result.metrics.effective_number_of_assets < 1.5


@pytest.mark.asyncio
async def test_optimize_rejects_too_few_symbols_and_too_little_history() -> None:
    service = _service({"AAA": _series(400, 0.10, 0.02, 30)})

    with pytest.raises(ValueError, match="at least two symbols"):
        await service.optimize(OptimizePortfolioRequest(symbols=("AAA",)))

    thin = _service(
        {
            "AAA": _series(10, 0.10, 0.02, 5),
            "BBB": _series(10, 0.08, 0.03, 5, phase=1.0),
        }
    )
    with pytest.raises(ValueError, match="overlapping price observations"):
        await thin.optimize(OptimizePortfolioRequest(symbols=("AAA", "BBB")))


@pytest.mark.asyncio
async def test_unknown_objective_is_rejected_with_the_allowed_list() -> None:
    service = _service({"AAA": _series(200, 0.1, 0.02, 30)})

    with pytest.raises(ValueError, match="max_sharpe"):
        await service.optimize(
            OptimizePortfolioRequest(symbols=("AAA", "BBB"), objective="moon_shot")
        )
