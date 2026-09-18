from __future__ import annotations

import math
from collections.abc import Sequence

from backend.modules.prediction.application.models import PredictionModelContract
from backend.modules.prediction.domain.entities import ModelOutput, PredictionDirection

# Probability thresholds that turn a forecast into a directional call. Kept
# identical to the logistic baseline so the models stay comparable.
_UP_THRESHOLD = 0.55
_DOWN_THRESHOLD = 0.45

# Below this many returns any time-series fit is noise, so the models decline
# to make a call rather than emit a confident-looking number.
_MIN_OBSERVATIONS = 30


def _normal_cdf(x: float) -> float:
    """P(Z <= x) for a standard normal, via the error function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _log_returns(closes: Sequence[float]) -> list[float]:
    """Continuously-compounded returns.

    Log returns are used rather than simple returns because they add across
    time: the h-day return is the sum of h daily returns, which is what makes
    the horizon scaling below exact rather than approximate.
    """

    returns: list[float] = []
    for i in range(1, len(closes)):
        previous, current = float(closes[i - 1]), float(closes[i])
        if previous <= 0.0 or current <= 0.0:
            continue
        returns.append(math.log(current / previous))
    return returns


def _neutral(features: dict[str, float] | None = None) -> ModelOutput:
    return ModelOutput(
        direction=PredictionDirection.NEUTRAL,
        probability_up=0.5,
        expected_return_pct=0.0,
        confidence=0.0,
        features=features or {},
    )


def _to_output(
    expected_log_return: float,
    horizon_sigma: float,
    features: dict[str, float],
) -> ModelOutput:
    """Turn a (drift, dispersion) forecast into the shared ModelOutput shape.

    Treating the h-day log return as normal with mean ``expected_log_return``
    and standard deviation ``horizon_sigma`` gives the probability of an up
    move directly as the mass above zero — no calibration constant invented.
    """

    if horizon_sigma <= 1e-12:
        return _neutral(features)

    probability_up = _normal_cdf(expected_log_return / horizon_sigma)
    # expm1 converts the log return back to a simple percentage return.
    expected_return_pct = math.expm1(expected_log_return) * 100.0

    direction = PredictionDirection.NEUTRAL
    if probability_up > _UP_THRESHOLD:
        direction = PredictionDirection.UP
    elif probability_up < _DOWN_THRESHOLD:
        direction = PredictionDirection.DOWN

    return ModelOutput(
        direction=direction,
        probability_up=probability_up,
        expected_return_pct=expected_return_pct,
        confidence=abs(probability_up - 0.5) * 2.0,
        features=features,
    )


class EwmaDriftModel(PredictionModelContract):
    """Exponentially-weighted drift and volatility forecast.

    A genuine time-series model rather than a classifier: it estimates the
    conditional mean and variance of the return process, weighting recent
    observations more heavily via a decay factor (0.94 is the RiskMetrics
    convention for daily data). Drift scales with the horizon and dispersion
    with its square root — the standard random-walk scaling — so the same fit
    answers 1-day and 21-day questions consistently.

    Deterministic: no randomness, no iteration count to tune.
    """

    name = "ewma-drift-v1"

    def __init__(self, decay: float = 0.94) -> None:
        if not 0.0 < decay < 1.0:
            raise ValueError("EWMA decay must be strictly between 0 and 1.")
        self._decay = decay

    def predict(
        self,
        closes: Sequence[float],
        horizon_days: int = 1,
        event_score: float = 0.0,
    ) -> ModelOutput:
        returns = _log_returns(closes)
        if len(returns) < _MIN_OBSERVATIONS:
            return _neutral()

        horizon = max(1, int(horizon_days))
        mean, variance = self._weighted_moments(returns)
        daily_sigma = math.sqrt(max(variance, 0.0))

        expected_log_return = mean * horizon
        horizon_sigma = daily_sigma * math.sqrt(horizon)

        return _to_output(
            expected_log_return,
            horizon_sigma,
            {
                "ewma_daily_drift": round(mean, 8),
                "ewma_daily_volatility": round(daily_sigma, 8),
                "ewma_annualized_volatility_pct": round(
                    daily_sigma * math.sqrt(252) * 100.0, 4
                ),
                "horizon_days": float(horizon),
            },
        )

    def _weighted_moments(self, returns: Sequence[float]) -> tuple[float, float]:
        """Exponentially-weighted (mean, variance) of the return series."""

        n = len(returns)
        # Most recent observation gets weight 1, each older one decays.
        weights = [self._decay ** (n - 1 - i) for i in range(n)]
        total_weight = sum(weights)

        mean = sum(w * r for w, r in zip(weights, returns)) / total_weight
        variance = (
            sum(w * (r - mean) ** 2 for w, r in zip(weights, returns)) / total_weight
        )
        return mean, variance


class Ar1Model(PredictionModelContract):
    """First-order autoregressive model on log returns, fit by OLS.

    Fits ``r_t = a + b * r_{t-1} + e``. The slope ``b`` is the one-lag
    autocorrelation: positive means short-term momentum, negative means
    short-term reversal — the effect that actually exists in daily equity data
    and that a price-level model cannot express.

    The h-step forecast is the sum of the mean-reverting path
    ``E[r_{t+k}] = mu + b^k (r_t - mu)``, and its variance accounts for the
    autoregressive accumulation of shocks rather than assuming independence.

    Stationarity requires |b| < 1, but the two boundaries fail differently and
    are handled differently:

      * ``b -> +1`` is a near unit root. The long-run mean ``a / (1 - b)``
        diverges, so the h-step formulas stop meaning anything and the model
        falls back to a driftless random walk.
      * ``b -> -1`` is *strong mean reversion* — a real and common signal in
        daily returns, where the long-run mean stays well behaved (the
        denominator approaches 2). Discarding it would throw away exactly the
        effect this model exists to capture, so it is merely clamped just
        inside the stationary region.
    """

    name = "ar1-v1"

    # How close to the +1 unit root we tolerate before giving up, and how
    # close to -1 we allow a reversal fit to sit.
    _UNIT_ROOT_LIMIT = 0.999
    _REVERSION_LIMIT = -0.99

    def predict(
        self,
        closes: Sequence[float],
        horizon_days: int = 1,
        event_score: float = 0.0,
    ) -> ModelOutput:
        returns = _log_returns(closes)
        if len(returns) < _MIN_OBSERVATIONS + 1:
            return _neutral()

        horizon = max(1, int(horizon_days))
        slope, intercept, residual_variance = self._fit(returns)

        if slope >= self._UNIT_ROOT_LIMIT:
            # Near unit root: the long-run mean diverges, so fall back to a
            # driftless random walk rather than extrapolate a broken formula.
            slope = 0.0
        elif slope < self._REVERSION_LIMIT:
            # Strong reversal — keep the signal, just hold it inside the
            # stationary region so the geometric sums stay bounded.
            slope = self._REVERSION_LIMIT

        long_run_mean = (
            intercept / (1.0 - slope) if abs(1.0 - slope) > 1e-9 else intercept
        )
        last_return = returns[-1]

        # Cumulative expected log return over the horizon.
        expected_log_return = 0.0
        deviation = last_return - long_run_mean
        for k in range(1, horizon + 1):
            expected_log_return += long_run_mean + (slope**k) * deviation

        # Var(sum of h AR(1) steps): shock at step k propagates through the
        # remaining steps with a geometric weight.
        variance = 0.0
        for k in range(1, horizon + 1):
            steps = horizon - k + 1
            if abs(1.0 - slope) > 1e-9:
                weight = (1.0 - slope**steps) / (1.0 - slope)
            else:
                weight = float(steps)
            variance += residual_variance * weight**2

        return _to_output(
            expected_log_return,
            math.sqrt(max(variance, 0.0)),
            {
                "ar1_slope": round(slope, 6),
                "ar1_intercept": round(intercept, 8),
                "ar1_long_run_mean": round(long_run_mean, 8),
                "ar1_residual_volatility": round(math.sqrt(residual_variance), 8),
                "horizon_days": float(horizon),
            },
        )

    def _fit(self, returns: Sequence[float]) -> tuple[float, float, float]:
        """OLS of r_t on r_{t-1}; returns (slope, intercept, residual variance)."""

        x = returns[:-1]
        y = returns[1:]
        n = len(x)

        mean_x = sum(x) / n
        mean_y = sum(y) / n

        covariance = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        variance_x = sum((xi - mean_x) ** 2 for xi in x)

        slope = covariance / variance_x if variance_x > 1e-18 else 0.0
        intercept = mean_y - slope * mean_x

        residuals = [yi - (intercept + slope * xi) for xi, yi in zip(x, y)]
        # n - 2 degrees of freedom: two parameters were estimated.
        denominator = max(n - 2, 1)
        residual_variance = sum(r * r for r in residuals) / denominator

        return slope, intercept, residual_variance


# Purpose:
# Genuine time-series forecasters for the prediction module — an EWMA
# drift/volatility model and an AR(1) model on log returns. Both are pure
# Python, deterministic, and horizon-aware, and both implement the same
# PredictionModelContract as the logistic baseline so they can be ensembled.
#
# What Should Not Live Here:
# - Price fetching or persistence (the application service owns those).
# - Blending multiple models (that is ensemble.py).

__all__ = ["Ar1Model", "EwmaDriftModel"]
