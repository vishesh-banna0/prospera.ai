from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import datetime

from backend.modules.company.domain.entities import CompanyRating, CompanyScore

# Trading days per year, used to annualize daily volatility.
_TRADING_DAYS = 252


def daily_returns(closes: Sequence[float]) -> list[float]:
    """Simple day-over-day returns from a chronological close-price series."""

    returns: list[float] = []
    for previous, current in zip(closes, closes[1:]):
        if previous > 0:
            returns.append((current - previous) / previous)
    return returns


def total_return_pct(closes: Sequence[float]) -> float:
    """Total percentage return from first to last close (0 if not computable)."""

    if len(closes) < 2 or closes[0] <= 0:
        return 0.0
    return (closes[-1] - closes[0]) / closes[0] * 100.0


def annualized_volatility_pct(returns: Sequence[float]) -> float:
    """Annualized volatility (%) of daily returns."""

    n = len(returns)
    if n < 2:
        return 0.0
    mean = sum(returns) / n
    variance = sum((r - mean) ** 2 for r in returns) / (n - 1)
    daily_std = math.sqrt(variance)
    return daily_std * math.sqrt(_TRADING_DAYS) * 100.0


def max_drawdown_pct(closes: Sequence[float]) -> float:
    """Largest peak-to-trough decline (%) over the series (>= 0)."""

    if not closes:
        return 0.0
    peak = closes[0]
    worst = 0.0
    for price in closes:
        peak = max(peak, price)
        if peak > 0:
            drawdown = (peak - price) / peak
            worst = max(worst, drawdown)
    return worst * 100.0


def growth_score(total_return: float) -> float:
    """Map a trailing total return (%) onto 0..100 (50 = flat).

    A logistic curve keeps extremes bounded: a big rally saturates near 100, a
    deep fall near 0, and modest moves stay close to the neutral midpoint.
    """

    return 100.0 / (1.0 + math.exp(-total_return / 25.0))


def risk_score(volatility: float, drawdown: float) -> float:
    """Blend annualized volatility and max drawdown into a 0..100 risk score.

    ~40% annualized vol or ~50% drawdown each read as clearly elevated risk;
    the two are averaged and clamped.
    """

    vol_component = min(100.0, volatility / 0.4)
    dd_component = min(100.0, drawdown / 0.5)
    return min(100.0, max(0.0, 0.5 * vol_component + 0.5 * dd_component))


def sentiment_score(event_weights: Sequence[float]) -> float:
    """Map importance-weighted event signals (each roughly -1..+1) to 0..100.

    50 means no events or a neutral balance; above 50 is net-positive news
    flow, below 50 net-negative.
    """

    if not event_weights:
        return 50.0
    average = sum(event_weights) / len(event_weights)
    average = max(-1.0, min(1.0, average))
    return 50.0 + average * 50.0


def rating_for(overall: float) -> CompanyRating:
    if overall >= 66.0:
        return CompanyRating.STRONG
    if overall >= 40.0:
        return CompanyRating.MODERATE
    return CompanyRating.WEAK


def score_company(
    symbol: str,
    as_of: datetime,
    closes: Sequence[float],
    event_weights: Sequence[float],
    company_name: str | None = None,
    sector: str | None = None,
    market_cap: str | None = None,
) -> CompanyScore:
    """Combine price history + event signals into a full company scorecard.

    Missing inputs degrade gracefully: no price history -> neutral growth/risk;
    no events -> neutral sentiment. The overall score weights growth and news
    positively and risk negatively.
    """

    returns = daily_returns(closes)
    tr = total_return_pct(closes)
    vol = annualized_volatility_pct(returns)
    dd = max_drawdown_pct(closes)

    growth = growth_score(tr) if len(closes) >= 2 else 50.0
    risk = risk_score(vol, dd) if len(returns) >= 2 else 50.0
    sentiment = sentiment_score(event_weights)

    # Reward growth and positive news, penalize risk. Weights sum to 1.
    overall = 0.4 * growth + 0.3 * sentiment + 0.3 * (100.0 - risk)

    rationale = (
        f"Trailing return {tr:+.1f}% over {len(closes)} sessions.",
        f"Annualized volatility {vol:.1f}%, max drawdown {dd:.1f}%.",
        f"News sentiment {'positive' if sentiment > 55 else 'negative' if sentiment < 45 else 'neutral'} "
        f"from {len(event_weights)} recent events.",
    )

    return CompanyScore(
        symbol=symbol,
        as_of=as_of,
        overall_score=overall,
        growth_score=growth,
        risk_score=risk,
        sentiment_score=sentiment,
        rating=rating_for(overall),
        company_name=company_name,
        sector=sector,
        market_cap=market_cap,
        event_count=len(event_weights),
        price_points=len(closes),
        rationale=rationale,
    )


# Purpose:
# Pure, deterministic scoring math for Phase 10 — no I/O, fully unit-testable.
#
# What Should Not Live Here:
# - Data fetching (the application service supplies closes + event weights).
# - Persistence / HTTP.
