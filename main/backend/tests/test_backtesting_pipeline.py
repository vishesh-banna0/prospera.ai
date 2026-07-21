from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from backend.modules.backtesting.application.dto import LumpSumRequest, SipRequest
from backend.modules.backtesting.application.services import BacktestService
from backend.modules.backtesting.domain.engine import (
    monthly_contribution_dates,
    run_backtest,
)
from backend.modules.backtesting.domain.entities import Strategy
from backend.modules.backtesting.domain.metrics import (
    cagr_pct,
    max_drawdown_pct,
    xirr,
)
from backend.modules.market_data.application.dto import (
    HistoricalPricePointView,
    HistoricalPriceSeriesView,
)


# ---- pure metrics ----------------------------------------------------------


def test_cagr_doubling_over_one_year() -> None:
    assert cagr_pct(100.0, 200.0, 1.0) == pytest.approx(100.0)


def test_max_drawdown() -> None:
    assert max_drawdown_pct([100, 120, 60, 90]) == pytest.approx(50.0)


def test_xirr_simple_doubling() -> None:
    flows = [(date(2025, 1, 1), -1000.0), (date(2026, 1, 1), 2000.0)]
    # ~100% annual return over one year.
    assert xirr(flows) == pytest.approx(100.0, abs=1.0)


# ---- engine ----------------------------------------------------------------


def _series(start: date, days: int, daily_growth: float) -> list[tuple[date, float]]:
    return [
        (start + timedelta(days=i), 100.0 * ((1 + daily_growth) ** i))
        for i in range(days)
    ]


def test_lump_sum_backtest_on_uptrend() -> None:
    series = _series(date(2025, 1, 1), 260, 0.001)  # steady climb
    result = run_backtest(
        symbol="AAA",
        currency="INR",
        series=series,
        contributions=[(date(2025, 1, 1), 100000.0)],
        strategy=Strategy.LUMP_SUM,
    )
    assert result.metrics.total_invested == pytest.approx(100000.0)
    assert result.metrics.final_value > 100000.0  # made money on an uptrend
    assert result.metrics.profit > 0
    assert result.metrics.max_drawdown_pct == pytest.approx(0.0, abs=0.01)
    assert result.units > 0
    assert len(result.curve) > 0


def test_sip_accumulates_units_across_contributions() -> None:
    series = _series(date(2025, 1, 1), 400, 0.0005)
    dates = monthly_contribution_dates(date(2025, 1, 1), date(2026, 1, 1))
    assert len(dates) >= 12
    result = run_backtest(
        symbol="AAA",
        currency="INR",
        series=series,
        contributions=[(d, 5000.0) for d in dates],
        strategy=Strategy.SIP,
    )
    # Invested once per month; final value reflects accumulated units.
    assert result.metrics.total_invested == pytest.approx(5000.0 * len(dates))
    assert result.units > 0
    assert result.strategy == Strategy.SIP


# ---- service (offline stub) ------------------------------------------------


class _StubMarketData:
    def __init__(self, series: list[tuple[date, float]]) -> None:
        self._series = series

    async def get_historical_prices(self, request):
        prices = tuple(
            HistoricalPricePointView(
                timestamp=datetime(on.year, on.month, on.day, tzinfo=UTC),
                open_price=str(price),
                high_price=str(price),
                low_price=str(price),
                close_price=str(price),
                volume=1000,
            )
            for on, price in self._series
        )
        return HistoricalPriceSeriesView(
            symbol=request.symbol, currency="INR", prices=prices
        )


@pytest.mark.asyncio
async def test_service_lump_sum_and_sip() -> None:
    series = _series(date(2025, 1, 1), 300, 0.0008)
    service = BacktestService(market_data_service=_StubMarketData(series))

    lump = await service.run_lump_sum(
        LumpSumRequest(
            symbol="aaa",
            amount=100000.0,
            start_at=datetime(2025, 1, 1, tzinfo=UTC),
            end_at=datetime(2025, 12, 1, tzinfo=UTC),
        )
    )
    assert lump.symbol == "AAA"
    assert lump.currency == "INR"
    assert lump.metrics.final_value > 0

    sip = await service.run_sip(
        SipRequest(
            symbol="aaa",
            monthly_amount=5000.0,
            start_at=datetime(2025, 1, 1, tzinfo=UTC),
            end_at=datetime(2025, 10, 1, tzinfo=UTC),
        )
    )
    assert sip.strategy == "sip"
    assert sip.metrics.total_invested > 0


@pytest.mark.asyncio
async def test_service_raises_without_enough_history() -> None:
    service = BacktestService(market_data_service=_StubMarketData([(date(2025, 1, 1), 100.0)]))
    with pytest.raises(ValueError):
        await service.run_lump_sum(
            LumpSumRequest(
                symbol="AAA",
                amount=1000.0,
                start_at=datetime(2025, 1, 1, tzinfo=UTC),
                end_at=datetime(2025, 2, 1, tzinfo=UTC),
            )
        )
