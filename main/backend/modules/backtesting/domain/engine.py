from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from backend.modules.backtesting.domain.entities import (
    BacktestMetrics,
    BacktestResult,
    EquityPoint,
    Strategy,
)
from backend.modules.backtesting.domain.metrics import (
    annualized_volatility_pct,
    cagr_pct,
    daily_returns,
    max_drawdown_pct,
    sharpe_ratio,
    sortino_ratio,
    xirr,
)

# A price series is a chronological list of (trading date, price) pairs.
PriceSeries = Sequence[tuple[date, float]]


def monthly_contribution_dates(start: date, end: date) -> list[date]:
    """Month-by-month contribution dates from ``start`` up to ``end``."""

    dates: list[date] = []
    year, month = start.year, start.month
    day = start.day
    while True:
        # Clamp the day to a valid day-of-month (e.g. the 31st in February).
        for candidate_day in (day, 28, 1):
            try:
                current = date(year, month, candidate_day)
                break
            except ValueError:
                continue
        if current > end:
            break
        dates.append(current)
        month += 1
        if month > 12:
            month = 1
            year += 1
    return dates


def _price_on_or_after(series: PriceSeries, target: date) -> tuple[int, float] | None:
    for index, (on, price) in enumerate(series):
        if on >= target and price > 0:
            return index, price
    return None


def run_backtest(
    symbol: str,
    currency: str,
    series: PriceSeries,
    contributions: Sequence[tuple[date, float]],
    strategy: Strategy,
    risk_free_rate: float = 0.0,
    max_curve_points: int = 120,
) -> BacktestResult:
    """Replay a set of dated contributions against a historical price series.

    Each contribution buys units at the first available price on/after its date;
    units accumulate. Return metrics (total return, CAGR, XIRR) come from the
    actual cash flows and final value; risk metrics (volatility, Sharpe,
    Sortino, max drawdown) come from the underlying asset's daily returns — the
    standard single-asset interpretation, and it avoids contribution inflows
    being mistaken for gains.
    """

    if len(series) < 2:
        raise ValueError("A backtest needs at least two price points.")

    series = sorted(series, key=lambda item: item[0])
    prices = [price for _, price in series]
    dates = [on for on, _ in series]
    final_price = prices[-1]

    # Apply contributions -> accumulate units, remember cash-flow events.
    units = 0.0
    invested = 0.0
    applied: list[tuple[date, float]] = []  # (date actually invested, amount)
    for target, amount in sorted(contributions, key=lambda item: item[0]):
        if amount <= 0:
            continue
        found = _price_on_or_after(series, target)
        if found is None:
            continue
        index, price = found
        units += amount / price
        invested += amount
        applied.append((dates[index], amount))

    if invested <= 0 or units <= 0:
        raise ValueError("No contribution could be invested in the price window.")

    final_value = units * final_price
    profit = final_value - invested
    total_return_pct = (profit / invested) * 100.0
    years = max((dates[-1] - dates[0]).days / 365.0, 1e-9)

    cashflows: list[tuple[date, float]] = [(d, -a) for d, a in applied]
    cashflows.append((dates[-1], final_value))

    asset_returns = daily_returns(prices)
    portfolio_values = _portfolio_value_curve(series, applied)

    metrics = BacktestMetrics(
        total_invested=round(invested, 2),
        final_value=round(final_value, 2),
        profit=round(profit, 2),
        total_return_pct=round(total_return_pct, 2),
        cagr_pct=round(cagr_pct(invested, final_value, years), 2),
        xirr_pct=round(xirr(cashflows), 2),
        annualized_volatility_pct=round(annualized_volatility_pct(asset_returns), 2),
        sharpe_ratio=round(sharpe_ratio(asset_returns, risk_free_rate), 3),
        sortino_ratio=round(sortino_ratio(asset_returns, risk_free_rate), 3),
        max_drawdown_pct=round(max_drawdown_pct(portfolio_values), 2),
    )

    curve = _downsample_curve(series, applied, max_curve_points)

    return BacktestResult(
        symbol=symbol,
        strategy=strategy,
        currency=currency,
        start_date=dates[0],
        end_date=dates[-1],
        units=round(units, 6),
        metrics=metrics,
        curve=curve,
    )


def _portfolio_value_curve(
    series: PriceSeries, applied: Sequence[tuple[date, float]]
) -> list[float]:
    values: list[float] = []
    for on, price in series:
        units = sum(
            amount / _first_price_at_or_after(series, inv_date)
            for inv_date, amount in applied
            if inv_date <= on
        )
        values.append(units * price)
    return values


def _downsample_curve(
    series: PriceSeries, applied: Sequence[tuple[date, float]], max_points: int
) -> tuple[EquityPoint, ...]:
    step = max(1, len(series) // max_points)
    points: list[EquityPoint] = []
    for i in range(0, len(series), step):
        on, price = series[i]
        units = 0.0
        invested = 0.0
        for inv_date, amount in applied:
            if inv_date <= on:
                units += amount / _first_price_at_or_after(series, inv_date)
                invested += amount
        points.append(EquityPoint(on=on, invested=round(invested, 2), value=round(units * price, 2)))
    # Always include the final point.
    last_on, last_price = series[-1]
    units = sum(amount / _first_price_at_or_after(series, d) for d, amount in applied if d <= last_on)
    invested = sum(amount for d, amount in applied if d <= last_on)
    points.append(EquityPoint(on=last_on, invested=round(invested, 2), value=round(units * last_price, 2)))
    return tuple(points)


def _first_price_at_or_after(series: PriceSeries, target: date) -> float:
    for on, price in series:
        if on >= target and price > 0:
            return price
    return series[-1][1]
