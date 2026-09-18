from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import numpy as np

from backend.modules.market_data.application.dto import (
    HistoricalPriceRequest,
    QuoteRequest,
)
from backend.modules.portfolio.application.dto import (
    AllocationView,
    CorrelationRowView,
    OptimizePortfolioRequest,
    PortfolioMetricsView,
    PortfolioOptimizationView,
    PortfolioRiskRequest,
    PortfolioRiskView,
    RebalanceTradeView,
)
from backend.modules.portfolio.domain import risk as risk_analytics
from backend.modules.portfolio.domain.optimizer import (
    Objective,
    TRADING_DAYS,
    annualized_moments,
    daily_returns_matrix,
    optimize_weights,
)

logger = logging.getLogger(__name__)

# Below this many overlapping observations a covariance estimate is noise. Two
# months of daily data is already thin; less than that and we refuse rather
# than return confident-looking nonsense.
_MIN_OBSERVATIONS = 40

# Flag a position that dominates the portfolio's capital or its risk.
_CONCENTRATION_WEIGHT_PCT = 40.0
_CONCENTRATION_RISK_PCT = 50.0

# Don't emit a rebalancing trade for trivial drift — it would cost more in fees
# and attention than the tracking error it corrects.
_MIN_TRADE_FRACTION = 0.01


class PortfolioOptimizationService:
    """Application boundary for portfolio construction and portfolio risk.

    Pulls aligned price history through the market data service, estimates
    annualized moments, solves for target weights, and reports the result with
    a full risk decomposition. When the request names a simulator environment
    it also reads the live holdings, so the output includes current weights and
    the trades that would close the gap.

    Every objective is compared against an equal-weight baseline, because an
    optimizer that cannot beat equal weight is not worth its estimation error.
    """

    def __init__(
        self,
        market_data_service,
        holding_repository=None,
        environment_repository=None,
    ) -> None:
        self._market_data = market_data_service
        self._holdings = holding_repository
        self._environments = environment_repository

    # -- optimization -----------------------------------------------------

    async def optimize(
        self,
        request: OptimizePortfolioRequest,
    ) -> PortfolioOptimizationView:
        objective = self._coerce_objective(request.objective)
        lookback_days = max(60, min(int(request.lookback_days), 3650))
        notes: list[str] = []

        holdings = await self._load_holdings(request.environment_id)
        symbols = self._resolve_symbols(request.symbols, holdings)
        if len(symbols) < 2:
            raise ValueError(
                "Portfolio optimization needs at least two symbols. Pass "
                "`symbols`, or use an environment that holds two or more "
                "positions."
            )

        series, currency, skipped = await self._load_price_series(
            symbols, lookback_days
        )
        if skipped:
            notes.append(
                "Excluded (no usable price history): " + ", ".join(sorted(skipped))
            )
        if len(series) < 2:
            raise ValueError(
                "Could not load enough price history to optimize. At least two "
                "symbols need overlapping history in the lookback window."
            )

        aligned_symbols, returns = daily_returns_matrix(series)
        observations = int(returns.shape[0])
        if observations < _MIN_OBSERVATIONS:
            raise ValueError(
                f"Only {observations} overlapping price observations across "
                f"these symbols; at least {_MIN_OBSERVATIONS} are needed for a "
                "meaningful covariance estimate. Widen `lookback_days` or drop "
                "recently-listed symbols."
            )

        mean, cov = annualized_moments(returns)
        weights = optimize_weights(
            objective,
            mean,
            cov,
            risk_free_rate=request.risk_free_rate,
            max_weight=request.max_weight,
        )
        equal_weights = np.full(len(aligned_symbols), 1.0 / len(aligned_symbols))

        optimized = risk_analytics.analyze(
            weights, mean, cov, returns, request.risk_free_rate
        )
        baseline = risk_analytics.analyze(
            equal_weights, mean, cov, returns, request.risk_free_rate
        )
        if optimized.sharpe_ratio <= baseline.sharpe_ratio and objective in (
            Objective.MAX_SHARPE,
            Objective.MIN_VARIANCE,
        ):
            notes.append(
                "The optimized portfolio does not beat equal weight on Sharpe "
                "over this window — treat the weights as fragile and prefer "
                "the simpler allocation."
            )

        current_weights = self._current_weight_map(holdings, aligned_symbols)
        allocations = self._build_allocations(
            aligned_symbols, weights, mean, cov, current_weights
        )
        trades = await self._build_trades(
            aligned_symbols, weights, holdings, currency
        )

        return PortfolioOptimizationView(
            objective=objective.value,
            symbols=aligned_symbols,
            allocations=allocations,
            optimized=self._to_metrics(optimized),
            equal_weight_baseline=self._to_metrics(baseline),
            correlations=self._to_correlations(aligned_symbols, cov),
            trades=trades,
            observations=observations,
            lookback_days=lookback_days,
            currency=currency,
            notes=tuple(notes),
        )

    # -- risk of what is actually held ------------------------------------

    async def analyze_holdings(
        self,
        request: PortfolioRiskRequest,
    ) -> PortfolioRiskView:
        """Risk decomposition of an environment's current positions, as held."""

        holdings = await self._load_holdings(request.environment_id)
        if not holdings:
            raise ValueError(
                f"Environment {request.environment_id} has no holdings to analyze."
            )

        lookback_days = max(60, min(int(request.lookback_days), 3650))
        symbols = tuple(sorted({h["symbol"] for h in holdings}))
        series, currency, _ = await self._load_price_series(symbols, lookback_days)
        if len(series) < 1:
            raise ValueError("Could not load price history for the held symbols.")

        aligned_symbols, returns = daily_returns_matrix(series)
        observations = int(returns.shape[0])
        mean, cov = annualized_moments(returns)

        weight_map = self._current_weight_map(holdings, aligned_symbols)
        weights = np.asarray(
            [weight_map.get(symbol, 0.0) for symbol in aligned_symbols],
            dtype=np.float64,
        )
        total = weights.sum()
        if total <= 0.0:
            raise ValueError("Holdings have no market value to analyze.")
        weights = weights / total

        metrics = risk_analytics.analyze(
            weights, mean, cov, returns, request.risk_free_rate
        )
        contributions = risk_analytics.risk_contributions(weights, cov)

        allocations = tuple(
            AllocationView(
                symbol=symbol,
                target_weight_pct=round(float(weight) * 100.0, 2),
                current_weight_pct=round(float(weight) * 100.0, 2),
                weight_change_pct=0.0,
                risk_contribution_pct=round(float(contribution) * 100.0, 2),
                annualized_return_pct=round(float(mean[i]) * 100.0, 2),
                annualized_volatility_pct=round(
                    float(np.sqrt(max(cov[i, i], 0.0))) * 100.0, 2
                ),
            )
            for i, (symbol, weight, contribution) in enumerate(
                zip(aligned_symbols, weights, contributions)
            )
        )

        return PortfolioRiskView(
            environment_id=request.environment_id,
            symbols=aligned_symbols,
            allocations=allocations,
            metrics=self._to_metrics(metrics),
            correlations=self._to_correlations(aligned_symbols, cov),
            concentration_warnings=self._concentration_warnings(allocations, metrics),
            observations=observations,
            currency=currency,
        )

    # -- helpers -----------------------------------------------------------

    def _coerce_objective(self, raw: str | None) -> Objective:
        try:
            return Objective(str(raw or "max_sharpe").strip().lower())
        except ValueError as exc:
            allowed = ", ".join(o.value for o in Objective)
            raise ValueError(
                f"Unknown objective '{raw}'. Choose one of: {allowed}."
            ) from exc

    async def _load_holdings(self, environment_id: str | None) -> list[dict]:
        """Current positions as plain dicts, or [] when not applicable.

        Returns dicts rather than domain entities so this module stays
        independent of the simulator's value objects — it only needs symbol,
        quantity, and cost.
        """

        if not environment_id or self._holdings is None:
            return []
        try:
            holdings = await self._holdings.list_by_environment(environment_id)
        except Exception as exc:
            logger.warning(
                "Could not load holdings for environment %s: %s", environment_id, exc
            )
            return []

        result: list[dict] = []
        for holding in holdings:
            try:
                quantity = float(holding.quantity.value)
            except (AttributeError, TypeError, ValueError):
                continue
            if quantity <= 0:
                continue
            result.append(
                {
                    "symbol": str(holding.symbol).upper(),
                    "quantity": quantity,
                    "average_cost": Decimal(str(holding.average_cost.amount)),
                }
            )
        return result

    def _resolve_symbols(
        self,
        requested: tuple[str, ...],
        holdings: list[dict],
    ) -> tuple[str, ...]:
        if requested:
            cleaned = {s.strip().upper() for s in requested if s and s.strip()}
        else:
            cleaned = {h["symbol"] for h in holdings}
        return tuple(sorted(cleaned))

    async def _load_price_series(
        self,
        symbols: tuple[str, ...],
        lookback_days: int,
    ) -> tuple[dict[str, list[float]], str, list[str]]:
        """Close-price history per symbol, plus the currency and any dropouts.

        A symbol that fails to load is skipped rather than failing the whole
        request: one delisted or mistyped ticker should not block optimizing
        the rest of the portfolio.
        """

        end_at = datetime.now(UTC)
        start_at = end_at - timedelta(days=lookback_days)

        series: dict[str, list[float]] = {}
        currency = "INR"
        skipped: list[str] = []

        for symbol in symbols:
            try:
                view = await self._market_data.get_historical_prices(
                    HistoricalPriceRequest(
                        symbol=symbol,
                        start_at=start_at,
                        end_at=end_at,
                        auto_sync=True,
                    )
                )
            except Exception as exc:
                logger.warning("No price history for %s: %s", symbol, exc)
                skipped.append(symbol)
                continue

            closes: list[float] = []
            for point in view.prices:
                try:
                    closes.append(float(point.close_price))
                except (TypeError, ValueError):
                    continue
            if len(closes) < 2:
                skipped.append(symbol)
                continue

            series[symbol] = closes
            currency = str(view.currency) or currency

        return series, currency, skipped

    def _current_weight_map(
        self,
        holdings: list[dict],
        symbols: tuple[str, ...],
    ) -> dict[str, float]:
        """Current capital weights, valued at average cost.

        Cost basis is used rather than live quotes so this stays a single
        round trip; the live-value path is ``analyze_holdings`` via the
        simulator's own performance view.
        """

        if not holdings:
            return {}
        values = {
            h["symbol"]: float(h["average_cost"]) * h["quantity"] for h in holdings
        }
        total = sum(values.values())
        if total <= 0:
            return {}
        return {symbol: values.get(symbol, 0.0) / total for symbol in symbols}

    def _build_allocations(
        self,
        symbols: tuple[str, ...],
        weights: np.ndarray,
        mean: np.ndarray,
        cov: np.ndarray,
        current_weights: dict[str, float],
    ) -> tuple[AllocationView, ...]:
        contributions = risk_analytics.risk_contributions(weights, cov)
        allocations: list[AllocationView] = []
        for i, symbol in enumerate(symbols):
            current = current_weights.get(symbol)
            target_pct = round(float(weights[i]) * 100.0, 2)
            current_pct = None if current is None else round(current * 100.0, 2)
            allocations.append(
                AllocationView(
                    symbol=symbol,
                    target_weight_pct=target_pct,
                    current_weight_pct=current_pct,
                    weight_change_pct=(
                        None if current_pct is None
                        else round(target_pct - current_pct, 2)
                    ),
                    risk_contribution_pct=round(float(contributions[i]) * 100.0, 2),
                    annualized_return_pct=round(float(mean[i]) * 100.0, 2),
                    annualized_volatility_pct=round(
                        float(np.sqrt(max(cov[i, i], 0.0))) * 100.0, 2
                    ),
                )
            )
        allocations.sort(key=lambda a: a.target_weight_pct, reverse=True)
        return tuple(allocations)

    async def _build_trades(
        self,
        symbols: tuple[str, ...],
        weights: np.ndarray,
        holdings: list[dict],
        currency: str,
    ) -> tuple[RebalanceTradeView, ...]:
        """Trades that would move current holdings to the target weights."""

        if not holdings:
            return ()

        values = {
            h["symbol"]: float(h["average_cost"]) * h["quantity"] for h in holdings
        }
        total = sum(values.values())
        if total <= 0:
            return ()

        target_by_symbol = dict(zip(symbols, (float(w) for w in weights)))
        trades: list[RebalanceTradeView] = []

        for symbol in sorted(set(values) | set(target_by_symbol)):
            current_value = values.get(symbol, 0.0)
            target_value = target_by_symbol.get(symbol, 0.0) * total
            delta = target_value - current_value
            if abs(delta) < total * _MIN_TRADE_FRACTION:
                continue
            trades.append(
                RebalanceTradeView(
                    symbol=symbol,
                    action="buy" if delta > 0 else "sell",
                    amount=f"{abs(delta):.2f}",
                    reason=(
                        f"Move {symbol} from "
                        f"{current_value / total * 100.0:.1f}% to "
                        f"{target_by_symbol.get(symbol, 0.0) * 100.0:.1f}% of the "
                        "portfolio."
                    ),
                )
            )
        trades.sort(key=lambda t: float(t.amount), reverse=True)
        return tuple(trades)

    def _to_correlations(
        self,
        symbols: tuple[str, ...],
        cov: np.ndarray,
    ) -> tuple[CorrelationRowView, ...]:
        matrix = risk_analytics.correlation_matrix(cov)
        return tuple(
            CorrelationRowView(
                symbol=symbol,
                correlations=tuple(round(float(value), 3) for value in matrix[i]),
            )
            for i, symbol in enumerate(symbols)
        )

    def _to_metrics(self, analysis: risk_analytics.PortfolioRisk) -> PortfolioMetricsView:
        return PortfolioMetricsView(
            expected_return_pct=analysis.expected_return_pct,
            volatility_pct=analysis.volatility_pct,
            sharpe_ratio=analysis.sharpe_ratio,
            diversification_ratio=analysis.diversification_ratio,
            effective_number_of_assets=analysis.effective_number_of_assets,
            max_drawdown_pct=analysis.max_drawdown_pct,
            historical_return_pct=analysis.historical_return_pct,
        )

    def _concentration_warnings(
        self,
        allocations: tuple[AllocationView, ...],
        metrics: PortfolioMetricsView,
    ) -> tuple[str, ...]:
        warnings: list[str] = []
        for allocation in allocations:
            if (allocation.current_weight_pct or 0.0) >= _CONCENTRATION_WEIGHT_PCT:
                warnings.append(
                    f"{allocation.symbol} is {allocation.current_weight_pct:.1f}% "
                    "of capital — a single-name shock would move the whole "
                    "portfolio."
                )
            if allocation.risk_contribution_pct >= _CONCENTRATION_RISK_PCT:
                warnings.append(
                    f"{allocation.symbol} contributes "
                    f"{allocation.risk_contribution_pct:.1f}% of total portfolio "
                    "risk, more than its capital weight suggests."
                )
        if metrics.diversification_ratio < 1.1 and len(allocations) > 1:
            warnings.append(
                "Diversification ratio is near 1.0 — these holdings move "
                "together, so holding several of them is close to holding one."
            )
        if metrics.effective_number_of_assets < 2.0 and len(allocations) > 2:
            warnings.append(
                f"{len(allocations)} positions but an effective count of "
                f"{metrics.effective_number_of_assets:.1f} — the portfolio "
                "behaves as though it holds far fewer."
            )
        return tuple(warnings)


# Purpose:
# Application boundary for portfolio optimization and portfolio-level risk:
# fetch history -> estimate moments -> solve weights -> explain the result and
# the trades that reach it.
#
# What Should Not Live Here:
# - The optimization math (domain/optimizer.py) or risk math (domain/risk.py).
# - HTTP concerns (the route owns those).
# - Executing trades — this module recommends, the simulator executes.

__all__ = ["PortfolioOptimizationService", "TRADING_DAYS"]
