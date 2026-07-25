from __future__ import annotations

import logging
from datetime import date, datetime

from backend.modules.backtesting.application.dto import (
    BacktestResultView,
    BenchmarkComparisonView,
    EquityPointView,
    LumpSumRequest,
    MetricsView,
    SipRequest,
)
from backend.modules.backtesting.domain.engine import (
    monthly_contribution_dates,
    run_backtest,
)
from backend.modules.backtesting.domain.entities import (
    BacktestMetrics,
    BacktestResult,
    Strategy,
)
from backend.modules.market_data.application.dto import HistoricalPriceRequest

logger = logging.getLogger(__name__)

# Default index to benchmark against when the caller doesn't specify one. NIFTY
# 50 (^NSEI) matches Prospera's INR-first, India-centric focus. yfinance serves
# its history through the same market-data path used for any other symbol.
DEFAULT_BENCHMARK_SYMBOL = "^NSEI"


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
        benchmark = await self._run_benchmark(
            request.benchmark_symbol,
            portfolio_symbol=symbol,
            contributions=contributions,
            start_at=request.start_at,
            end_at=request.end_at,
            strategy=Strategy.LUMP_SUM,
            portfolio_metrics=result.metrics,
        )
        return self._to_view(result, benchmark)

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
        benchmark = await self._run_benchmark(
            request.benchmark_symbol,
            portfolio_symbol=symbol,
            contributions=contributions,
            start_at=request.start_at,
            end_at=request.end_at,
            strategy=Strategy.SIP,
            portfolio_metrics=result.metrics,
        )
        return self._to_view(result, benchmark)

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

    def _resolve_benchmark_symbol(
        self, requested: str | None, portfolio_symbol: str
    ) -> str | None:
        """Decide which benchmark to run, or None to skip it.

        None -> app default (NIFTY 50); an explicit empty string -> disabled;
        and a benchmark equal to the portfolio symbol is skipped (comparing a
        symbol to itself is meaningless).
        """
        if requested is not None and requested.strip() == "":
            return None
        candidate = (requested or DEFAULT_BENCHMARK_SYMBOL).strip().upper()
        if not candidate or candidate == portfolio_symbol:
            return None
        return candidate

    async def _run_benchmark(
        self,
        requested_symbol: str | None,
        *,
        portfolio_symbol: str,
        contributions: list[tuple[date, float]],
        start_at: datetime,
        end_at: datetime,
        strategy: Strategy,
        portfolio_metrics: BacktestMetrics,
    ) -> BenchmarkComparisonView | None:
        """Replay the same contributions against the benchmark index.

        Runs the identical cash flows through the same engine so the metrics are
        directly comparable. Any failure to load the benchmark (missing/short
        history, bad symbol) is swallowed — the primary backtest still returns,
        just without a comparison.
        """
        benchmark_symbol = self._resolve_benchmark_symbol(
            requested_symbol, portfolio_symbol
        )
        if benchmark_symbol is None:
            return None

        try:
            series, currency = await self._load_series_with_currency(
                benchmark_symbol, start_at, end_at
            )
            result = run_backtest(
                symbol=benchmark_symbol,
                currency=currency,
                series=series,
                contributions=contributions,
                strategy=strategy,
            )
        except Exception as exc:
            logger.info(
                "Benchmark %s unavailable (%s); returning result without comparison.",
                benchmark_symbol,
                exc,
            )
            return None

        m = result.metrics
        return BenchmarkComparisonView(
            symbol=result.symbol,
            currency=result.currency,
            metrics=self._metrics_view(m),
            excess_return_pct=round(
                portfolio_metrics.total_return_pct - m.total_return_pct, 2
            ),
            excess_cagr_pct=round(portfolio_metrics.cagr_pct - m.cagr_pct, 2),
            outperformed=portfolio_metrics.total_return_pct > m.total_return_pct,
        )

    def _metrics_view(self, m: BacktestMetrics) -> MetricsView:
        return MetricsView(
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
        )

    def _to_view(
        self,
        result: BacktestResult,
        benchmark: BenchmarkComparisonView | None = None,
    ) -> BacktestResultView:
        return BacktestResultView(
            symbol=result.symbol,
            strategy=result.strategy.value,
            currency=result.currency,
            start_date=result.start_date,
            end_date=result.end_date,
            units=result.units,
            metrics=self._metrics_view(result.metrics),
            curve=tuple(
                EquityPointView(on=p.on, invested=p.invested, value=p.value)
                for p in result.curve
            ),
            benchmark=benchmark,
        )
