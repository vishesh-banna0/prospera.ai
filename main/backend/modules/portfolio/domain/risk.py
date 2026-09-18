from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from backend.modules.portfolio.domain.optimizer import TRADING_DAYS


@dataclass(frozen=True, slots=True)
class PortfolioRisk:
    """Portfolio-level risk analytics for one set of weights.

    Distinct from the per-asset metrics elsewhere in the codebase: these
    describe the portfolio as a whole, which is where covariance actually
    matters. A basket of individually risky assets can be far safer than its
    members, and a basket of individually safe but correlated assets can be
    far riskier — neither is visible from single-asset numbers.
    """

    expected_return_pct: float
    volatility_pct: float
    sharpe_ratio: float
    diversification_ratio: float
    effective_number_of_assets: float
    max_drawdown_pct: float
    historical_return_pct: float


def portfolio_return(weights: np.ndarray, mean: np.ndarray) -> float:
    return float(weights @ mean)


def portfolio_volatility(weights: np.ndarray, cov: np.ndarray) -> float:
    return float(np.sqrt(max(weights @ cov @ weights, 0.0)))


def sharpe_ratio(
    weights: np.ndarray,
    mean: np.ndarray,
    cov: np.ndarray,
    risk_free_rate: float = 0.0,
) -> float:
    volatility = portfolio_volatility(weights, cov)
    if volatility <= 1e-12:
        return 0.0
    return (portfolio_return(weights, mean) - risk_free_rate) / volatility


def risk_contributions(weights: np.ndarray, cov: np.ndarray) -> np.ndarray:
    """Each asset's share of total portfolio risk, summing to 1.

    Capital weight and risk weight are not the same thing: a 10% position in
    an asset twice as volatile as the rest contributes far more than 10% of
    the portfolio's risk. This is the number that tells you where the risk
    actually sits, computed as the standard Euler decomposition
    ``w_i * (Σw)_i / (w'Σw)``.
    """

    variance = float(weights @ cov @ weights)
    if variance <= 1e-18:
        return np.zeros_like(weights)
    return weights * (cov @ weights) / variance


def diversification_ratio(weights: np.ndarray, cov: np.ndarray) -> float:
    """Weighted average asset volatility / portfolio volatility.

    1.0 means diversification bought nothing (perfectly correlated holdings);
    higher is better. This is the direct measure of whether a portfolio's
    holdings are genuinely different bets or the same bet written several
    times — the thing a position count cannot tell you.
    """

    volatility = portfolio_volatility(weights, cov)
    if volatility <= 1e-12:
        return 1.0
    weighted_average = float(weights @ np.sqrt(np.maximum(np.diag(cov), 0.0)))
    return weighted_average / volatility


def effective_number_of_assets(weights: np.ndarray) -> float:
    """Inverse Herfindahl index: how many positions the portfolio *behaves* like.

    Ten holdings where one is 90% of capital has an effective count near 1.2,
    not 10. This is the concentration measure that survives contact with an
    unbalanced portfolio.
    """

    squared = float(np.sum(np.square(weights)))
    if squared <= 1e-18:
        return 0.0
    return 1.0 / squared


def correlation_matrix(cov: np.ndarray) -> np.ndarray:
    volatilities = np.sqrt(np.maximum(np.diag(cov), 1e-18))
    outer = np.outer(volatilities, volatilities)
    return np.clip(cov / outer, -1.0, 1.0)


def historical_performance(
    returns: np.ndarray,
    weights: np.ndarray,
) -> tuple[float, float]:
    """Replay the weights over the return history -> (total return %, max DD %).

    Assumes the weights are held constant (rebalanced each period), which is
    the like-for-like way to compare candidate allocations over the same
    window. Reported alongside the forward-looking figures because two
    portfolios with the same expected return are not equivalent if one got
    there through a far deeper drawdown.
    """

    if returns.size == 0 or weights.size == 0:
        return 0.0, 0.0

    portfolio_returns = returns @ weights
    equity = np.cumprod(1.0 + portfolio_returns)
    total_return_pct = float((equity[-1] - 1.0) * 100.0)

    running_peak = np.maximum.accumulate(equity)
    drawdowns = (running_peak - equity) / np.maximum(running_peak, 1e-18)
    return total_return_pct, float(drawdowns.max() * 100.0)


def analyze(
    weights: np.ndarray,
    mean: np.ndarray,
    cov: np.ndarray,
    returns: np.ndarray,
    risk_free_rate: float = 0.0,
) -> PortfolioRisk:
    """Full risk readout for one allocation."""

    historical_return_pct, max_drawdown_pct = historical_performance(returns, weights)
    return PortfolioRisk(
        expected_return_pct=round(portfolio_return(weights, mean) * 100.0, 2),
        volatility_pct=round(portfolio_volatility(weights, cov) * 100.0, 2),
        sharpe_ratio=round(sharpe_ratio(weights, mean, cov, risk_free_rate), 3),
        diversification_ratio=round(diversification_ratio(weights, cov), 3),
        effective_number_of_assets=round(effective_number_of_assets(weights), 2),
        max_drawdown_pct=round(max_drawdown_pct, 2),
        historical_return_pct=round(historical_return_pct, 2),
    )


# Purpose:
# Portfolio-level risk analytics — the covariance-aware view that single-asset
# metrics cannot provide. Pure functions over numpy arrays.
#
# What Should Not Live Here:
# - Weight solving (that is optimizer.py).
# - Price fetching or persistence.

__all__ = [
    "PortfolioRisk",
    "TRADING_DAYS",
    "analyze",
    "correlation_matrix",
    "diversification_ratio",
    "effective_number_of_assets",
    "historical_performance",
    "portfolio_return",
    "portfolio_volatility",
    "risk_contributions",
    "sharpe_ratio",
]
