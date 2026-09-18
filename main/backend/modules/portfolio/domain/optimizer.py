from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum

import numpy as np

# Trading days in a year — the standard annualization factor for daily returns.
TRADING_DAYS = 252

# Expected returns estimated from a sample average carry large error, and a
# mean-variance optimizer amplifies that error by piling weight into whichever
# asset happens to show the highest estimate. Shrinking each asset's mean
# toward the cross-sectional average pulls the optimizer back toward sensible
# portfolios. 0.0 = trust the raw sample, 1.0 = ignore it entirely.
DEFAULT_MEAN_SHRINKAGE = 0.30

# The same problem afflicts the covariance matrix: sample covariances are
# unstable when the number of assets approaches the number of observations.
# Shrinking toward the diagonal (variances only, correlations damped) is a
# cheap stand-in for Ledoit-Wolf and keeps the matrix well conditioned.
DEFAULT_COVARIANCE_SHRINKAGE = 0.10


class Objective(StrEnum):
    """What the optimizer is being asked to maximize or minimize."""

    EQUAL_WEIGHT = "equal_weight"
    INVERSE_VOLATILITY = "inverse_volatility"
    MIN_VARIANCE = "min_variance"
    MAX_SHARPE = "max_sharpe"


def daily_returns_matrix(
    series_by_symbol: dict[str, Sequence[float]],
) -> tuple[tuple[str, ...], np.ndarray]:
    """Align price series and convert them to a (days x assets) return matrix.

    Assets rarely share an identical history: a recent listing, a trading
    holiday in one market, a gap in the provider's data. Rather than
    interpolate (which invents observations and understates volatility), this
    truncates every series to the most recent ``n`` points they all have. That
    biases toward the shortest history, which is the honest, conservative
    choice — the covariance is only estimated over data that actually overlaps.

    Symbols with fewer than two prices are dropped, since a single point yields
    no return.
    """

    usable = {
        symbol: [float(p) for p in prices]
        for symbol, prices in series_by_symbol.items()
        if prices is not None and len(prices) >= 2
    }
    if not usable:
        return (), np.empty((0, 0))

    window = min(len(prices) for prices in usable.values())
    symbols = tuple(sorted(usable))

    columns = []
    for symbol in symbols:
        prices = np.asarray(usable[symbol][-window:], dtype=np.float64)
        # Guard non-positive prices, which would make the ratio meaningless.
        prices = np.where(prices <= 0.0, np.nan, prices)
        rets = prices[1:] / prices[:-1] - 1.0
        columns.append(np.nan_to_num(rets, nan=0.0, posinf=0.0, neginf=0.0))

    return symbols, np.column_stack(columns)


def annualized_moments(
    returns: np.ndarray,
    mean_shrinkage: float = DEFAULT_MEAN_SHRINKAGE,
    covariance_shrinkage: float = DEFAULT_COVARIANCE_SHRINKAGE,
) -> tuple[np.ndarray, np.ndarray]:
    """Annualized (expected returns, covariance matrix), both shrunk.

    Returns are annualized by ``x252`` and covariance by the same factor
    (variance scales with time under the usual i.i.d. assumption).
    """

    if returns.size == 0:
        return np.empty(0), np.empty((0, 0))

    mean = returns.mean(axis=0) * TRADING_DAYS
    # ddof=1: sample covariance, since these are estimates from a sample.
    cov = np.cov(returns, rowvar=False, ddof=1) * TRADING_DAYS
    cov = np.atleast_2d(cov)

    if mean_shrinkage > 0.0 and mean.size > 1:
        grand_mean = float(mean.mean())
        mean = (1.0 - mean_shrinkage) * mean + mean_shrinkage * grand_mean

    if covariance_shrinkage > 0.0 and cov.shape[0] > 1:
        target = np.diag(np.diag(cov))
        cov = (1.0 - covariance_shrinkage) * cov + covariance_shrinkage * target

    # Nudge the diagonal so the matrix is positive definite even if two assets
    # are perfectly collinear (identical or duplicated series).
    cov = cov + np.eye(cov.shape[0]) * 1e-10
    return mean, cov


def _project_capped_simplex(vector: np.ndarray, max_weight: float) -> np.ndarray:
    """Euclidean projection onto {w : 0 <= w <= max_weight, sum(w) = 1}.

    Solved by bisection on the offset ``theta`` in ``w = clip(v - theta, 0,
    cap)``: the clipped sum decreases monotonically in theta, so bisection
    finds the unique theta where it equals 1. Exact to floating point in ~60
    iterations, and it collapses to the standard simplex projection when the
    cap is 1.0. This is what keeps every optimizer iterate a valid long-only,
    fully-invested portfolio.
    """

    n = vector.size
    if n == 0:
        return vector
    # If the cap is too tight to reach a total of 1, it is unsatisfiable; the
    # only feasible answer is to hold every asset at the cap (equal weight).
    if max_weight * n <= 1.0:
        return np.full(n, 1.0 / n)

    low = float(vector.min() - 1.0)
    high = float(vector.max())
    for _ in range(60):
        theta = 0.5 * (low + high)
        total = np.clip(vector - theta, 0.0, max_weight).sum()
        if total > 1.0:
            low = theta
        else:
            high = theta
    return np.clip(vector - 0.5 * (low + high), 0.0, max_weight)


def _projected_gradient(
    gradient_fn,
    n_assets: int,
    max_weight: float,
    iterations: int,
    step: float,
) -> np.ndarray:
    """Maximize an objective over the capped simplex by projected ascent.

    Deliberately simple and deterministic: start at equal weight, take a fixed
    number of fixed-size steps, project back onto the feasible set after each.
    No random restarts and no solver dependency, so the same inputs always
    produce the same portfolio — which is what makes the results testable and
    a backtest reproducible. For the convex objectives here (and the
    quasi-concave Sharpe ratio) this converges reliably at this problem size.
    """

    weights = np.full(n_assets, 1.0 / n_assets)
    for _ in range(iterations):
        gradient = gradient_fn(weights)
        norm = np.linalg.norm(gradient)
        if not np.isfinite(norm) or norm == 0.0:
            break
        # Normalizing the gradient makes a single fixed step size work across
        # assets whose volatilities differ by an order of magnitude.
        weights = _project_capped_simplex(
            weights + step * gradient / norm, max_weight
        )
    return weights


def optimize_weights(
    objective: Objective,
    mean: np.ndarray,
    cov: np.ndarray,
    risk_free_rate: float = 0.0,
    max_weight: float = 1.0,
    iterations: int = 2000,
    step: float = 0.02,
) -> np.ndarray:
    """Target weights for one objective. Long-only and fully invested.

    ``max_weight`` caps any single position, the standard guard against an
    optimizer concentrating everything in one estimate it happens to like.
    """

    n = int(cov.shape[0])
    if n == 0:
        return np.empty(0)
    if n == 1:
        return np.ones(1)

    max_weight = float(min(max(max_weight, 1.0 / n), 1.0))

    if objective == Objective.EQUAL_WEIGHT:
        return np.full(n, 1.0 / n)

    if objective == Objective.INVERSE_VOLATILITY:
        vols = np.sqrt(np.maximum(np.diag(cov), 1e-12))
        raw = 1.0 / vols
        return _project_capped_simplex(raw / raw.sum(), max_weight)

    if objective == Objective.MIN_VARIANCE:
        # Minimize w'Σw  ->  ascend the negative gradient -2Σw.
        return _projected_gradient(
            lambda w: -2.0 * cov @ w, n, max_weight, iterations, step
        )

    if objective == Objective.MAX_SHARPE:
        excess = mean - risk_free_rate

        def gradient(w: np.ndarray) -> np.ndarray:
            variance = float(w @ cov @ w)
            if variance <= 1e-18:
                return excess
            sigma = np.sqrt(variance)
            numerator = float(w @ excess)
            # d/dw [ (w'μ_e) / sqrt(w'Σw) ]
            return excess / sigma - (numerator / (sigma**3)) * (cov @ w)

        return _projected_gradient(gradient, n, max_weight, iterations, step)

    raise ValueError(f"Unsupported optimization objective: {objective}")


# Purpose:
# The portfolio construction math: turn aligned price history into annualized
# moments, then solve for long-only target weights under four objectives.
# Pure and deterministic — no I/O, no persistence, no market-data client.
#
# What Should Not Live Here:
# - Fetching prices (the application service does that).
# - Reading current holdings or generating trades (application concerns).
# - Reporting/formatting (that is the DTO layer).
