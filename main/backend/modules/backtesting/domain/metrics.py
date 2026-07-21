from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import date

# Pure return/risk analytics used by the backtesting engine. No I/O, no
# dependencies — every function is deterministic and unit-testable. Risk metrics
# operate on a return series; return metrics operate on cash flows.

_TRADING_DAYS = 252


def daily_returns(values: Sequence[float]) -> list[float]:
    out: list[float] = []
    for prev, cur in zip(values, values[1:]):
        if prev > 0:
            out.append((cur - prev) / prev)
    return out


def cagr_pct(initial: float, final: float, years: float) -> float:
    """Compound annual growth rate (%). Requires a positive base and horizon."""

    if initial <= 0 or final <= 0 or years <= 0:
        return 0.0
    return ((final / initial) ** (1.0 / years) - 1.0) * 100.0


def annualized_volatility_pct(returns: Sequence[float]) -> float:
    n = len(returns)
    if n < 2:
        return 0.0
    mean = sum(returns) / n
    variance = sum((r - mean) ** 2 for r in returns) / (n - 1)
    return math.sqrt(variance) * math.sqrt(_TRADING_DAYS) * 100.0


def sharpe_ratio(returns: Sequence[float], risk_free_rate: float = 0.0) -> float:
    """Annualized Sharpe ratio from daily returns (risk_free_rate is annual)."""

    n = len(returns)
    if n < 2:
        return 0.0
    daily_rf = risk_free_rate / _TRADING_DAYS
    excess = [r - daily_rf for r in returns]
    mean = sum(excess) / n
    variance = sum((r - mean) ** 2 for r in excess) / (n - 1)
    std = math.sqrt(variance)
    if std == 0:
        return 0.0
    return (mean / std) * math.sqrt(_TRADING_DAYS)


def sortino_ratio(returns: Sequence[float], risk_free_rate: float = 0.0) -> float:
    """Annualized Sortino ratio (penalizes only downside deviation)."""

    n = len(returns)
    if n < 2:
        return 0.0
    daily_rf = risk_free_rate / _TRADING_DAYS
    excess = [r - daily_rf for r in returns]
    mean = sum(excess) / n
    downside = [min(0.0, r) for r in excess]
    downside_var = sum(d * d for d in downside) / n
    downside_std = math.sqrt(downside_var)
    if downside_std == 0:
        return 0.0
    return (mean / downside_std) * math.sqrt(_TRADING_DAYS)


def max_drawdown_pct(values: Sequence[float]) -> float:
    """Largest peak-to-trough decline (%) of a value series (>= 0)."""

    if not values:
        return 0.0
    peak = values[0]
    worst = 0.0
    for value in values:
        peak = max(peak, value)
        if peak > 0:
            worst = max(worst, (peak - value) / peak)
    return worst * 100.0


def xirr(cashflows: Sequence[tuple[date, float]], guess: float = 0.1) -> float:
    """Money-weighted annualized return (%) for dated, irregular cash flows.

    Convention: investments are negative, the final portfolio value is a
    positive terminal flow. Solves NPV(rate) = 0 with Newton's method and a
    bisection fallback for robustness, then returns the rate as a percentage.
    Returns 0.0 if it cannot converge to a sensible rate.
    """

    if len(cashflows) < 2:
        return 0.0
    base = cashflows[0][0]
    years = [((d - base).days) / 365.0 for d, _ in cashflows]
    amounts = [cf for _, cf in cashflows]

    def npv(rate: float) -> float:
        return sum(a / ((1.0 + rate) ** y) for a, y in zip(amounts, years))

    def dnpv(rate: float) -> float:
        return sum(-y * a / ((1.0 + rate) ** (y + 1.0)) for a, y in zip(amounts, years))

    # Newton's method.
    rate = guess
    for _ in range(100):
        try:
            f = npv(rate)
            d = dnpv(rate)
        except (OverflowError, ZeroDivisionError):
            break
        if abs(f) < 1e-7:
            return rate * 100.0
        if d == 0:
            break
        step = f / d
        new_rate = rate - step
        if new_rate <= -0.9999:
            new_rate = (rate - 0.9999) / 2.0
        if abs(new_rate - rate) < 1e-9:
            return new_rate * 100.0
        rate = new_rate

    # Bisection fallback on a wide bracket.
    low, high = -0.9999, 10.0
    f_low = npv(low)
    for _ in range(200):
        mid = (low + high) / 2.0
        f_mid = npv(mid)
        if abs(f_mid) < 1e-7:
            return mid * 100.0
        if (f_low < 0) == (f_mid < 0):
            low, f_low = mid, f_mid
        else:
            high = mid
    return 0.0
