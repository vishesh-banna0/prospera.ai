from __future__ import annotations

import logging
from datetime import date, datetime

from backend.modules.backtesting.application.dto import (
    BacktestResultView,
    EquityPointView,
    LumpSumRequest,
    MetricsView,
    SipRequest,
)
from backend.modules.backtesting.domain.engine import (
    monthly_contribution_dates,
    run_backtest,
)
from backend.modules.backtesting.domain.entities import BacktestResult, Strategy
from backend.modules.market_data.application.dto import HistoricalPriceRequest

logger = logging.getLogger(__name__)


class BacktestService:
    """Phase 15 application boundary — the reusable historical investment
    simulation service.

    Stateless: it pulls a historical price series (in INR) from the market data
    service, builds a contribution schedule for the chosen strategy, and runs
    the pure backtest engine. The same engine powers both user-facing "what if I
    had invested…" questions and future AI/RL strategy evaluation.
    """

    def __init__(self, market_data_service) -> None:
        self._market_data = market_data_service

    async def run_lump_sum(self, request: LumpSumRequest) -> BacktestResultView:
        symbol = request.symbol.strip().upper()
        series, currency = await self._load_series_with_currency(
            symbol, request.start_at, request.end_at
        )
        contributions = [(request.start_at.date(), float(request.amount))]
        result = run_backtest(
            symbol=symbol,
            currency=currency,
            series=series,
            contributions=contributions,
            strategy=Strategy.LUMP_SUM,
        )
        return self._to_view(result)

    async def run_sip(self, request: SipRequest) -> BacktestResultView:
        symbol = request.symbol.strip().upper()
        series, currency = await self._load_series_with_currency(
            symbol, request.start_at, request.end_at
        )
        contribution_dates = monthly_contribution_dates(
            request.start_at.date(), request.end_at.date()
        )
        contributions = [(d, float(request.monthly_amount)) for d in contribution_dates]
        result = run_backtest(
            symbol=symbol,
            currency=currency,
            series=series,
            contributions=contributions,
            strategy=Strategy.SIP,
        )
        return self._to_view(result)

    async def _load_series_with_currency(
        self, symbol: str, start_at: datetime, end_at: datetime
    ) -> tuple[list[tuple[date, float]], str]:
        try:
            view = await self._market_data.get_historical_prices(
                HistoricalPriceRequest(
                    symbol=symbol, start_at=start_at, end_at=end_at, auto_sync=True
                )
            )
        except Exception as exc:
            raise ValueError(
                f"Could not load price history for {symbol}: {exc}"
            ) from exc

        series: list[tuple[date, float]] = []
        for point in view.prices:
            try:
                series.append((point.timestamp.date(), float(point.close_price)))
            except (TypeError, ValueError):
                continue
        if len(series) < 2:
            raise ValueError(
                f"Not enough price history for {symbol} in the requested window."
            )
        return series, str(view.currency)

    def _to_view(self, result: BacktestResult) -> BacktestResultView:
        m = result.metrics
        return BacktestResultView(
            symbol=result.symbol,
            strategy=result.strategy.value,
            currency=result.currency,
            start_date=result.start_date,
            end_date=result.end_date,
            units=result.units,
            metrics=MetricsView(
                total_invested=m.total_invested,
                final_value=m.final_value,
                profit=m.profit,
                total_return_pct=m.total_return_pct,
                cagr_pct=m.cagr_pct,
                xirr_pct=m.xirr_pct,
                annualized_volatility_pct=m.annualized_volatility_pct,
                sharpe_ratio=m.sharpe_ratio,
                sortino_ratio=m.sortino_ratio,
                max_drawdown_pct=m.max_drawdown_pct,
            ),
            curve=tuple(
                EquityPointView(on=p.on, invested=p.invested, value=p.value)
                for p in result.curve
            ),
        )
