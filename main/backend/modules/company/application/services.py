from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from backend.modules.company.application.dto import (
    AnalyzeCompanyRequest,
    CompanyScoresView,
    CompanyScoreView,
)
from backend.modules.company.domain.entities import CompanyScore
from backend.modules.company.domain.repositories import CompanyScoreRepository
from backend.modules.company.domain.scoring import score_company
from backend.modules.events.domain.repositories import NewsEventRepository
from backend.modules.market_data.application.dto import HistoricalPriceRequest

logger = logging.getLogger(__name__)

# Signed sentiment direction and importance weighting used to turn a discrete
# news event into a single scalar the scorer can average.
_SENTIMENT_SIGN = {"positive": 1.0, "negative": -1.0, "neutral": 0.0}
_IMPORTANCE_WEIGHT = {"high": 1.0, "medium": 0.6, "low": 0.3}


class CompanyIntelligenceService:
    """Phase 10 application boundary.

    Pipeline: ``gather profile + price history + recent events -> score ->
    store``. Market data and events are read through their existing ports, so
    this service is fully testable offline with stubs. Market-data failures are
    non-fatal: the scorecard is still produced from whatever signals are
    available (events alone if prices are unreachable).
    """

    def __init__(
        self,
        market_data_service,
        event_repository: NewsEventRepository,
        score_repository: CompanyScoreRepository,
        commit: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self._market_data = market_data_service
        self._event_repository = event_repository
        self._score_repository = score_repository
        self._commit = commit

    async def analyze(self, request: AnalyzeCompanyRequest) -> CompanyScoreView:
        symbol = request.symbol.strip().upper()
        as_of = datetime.now(UTC)

        company_name, sector, market_cap = await self._load_profile(symbol)
        closes = await self._load_closes(symbol, request.lookback_days)
        event_weights = await self._load_event_weights(symbol, request.event_limit)

        score = score_company(
            symbol=symbol,
            as_of=as_of,
            closes=closes,
            event_weights=event_weights,
            company_name=company_name,
            sector=sector,
            market_cap=market_cap,
        )

        await self._score_repository.save(score)
        if self._commit is not None:
            await self._commit()

        return self._to_view(score)

    async def get_company(self, symbol: str) -> CompanyScoreView:
        score = await self._score_repository.get_latest(symbol.strip().upper())
        if score is None:
            raise ValueError(f"No company score found for '{symbol}'. Run analyze first.")
        return self._to_view(score)

    async def list_companies(self, limit: int = 50) -> CompanyScoresView:
        limit = min(max(1, int(limit)), 200)
        scores = await self._score_repository.list_latest(limit=limit)
        views = tuple(self._to_view(score) for score in scores)
        return CompanyScoresView(companies=views, count=len(views))

    async def _load_profile(
        self, symbol: str
    ) -> tuple[str | None, str | None, str | None]:
        try:
            profile = await self._market_data.get_company_profile(symbol)
            return profile.instrument_name, profile.sector, profile.market_cap
        except Exception as exc:
            logger.warning("Company profile unavailable for %s: %s", symbol, exc)
            return None, None, None

    async def _load_closes(self, symbol: str, lookback_days: int) -> list[float]:
        end_at = datetime.now(UTC)
        start_at = end_at - timedelta(days=max(1, lookback_days))
        try:
            series = await self._market_data.get_historical_prices(
                HistoricalPriceRequest(
                    symbol=symbol, start_at=start_at, end_at=end_at, auto_sync=True
                )
            )
        except Exception as exc:
            logger.warning("Price history unavailable for %s: %s", symbol, exc)
            return []

        closes: list[float] = []
        for point in series.prices:
            try:
                closes.append(float(point.close_price))
            except (TypeError, ValueError):
                continue
        return closes

    async def _load_event_weights(self, symbol: str, event_limit: int) -> list[float]:
        limit = min(max(1, int(event_limit)), 200)
        try:
            events = await self._event_repository.list_events(symbol=symbol, limit=limit)
        except Exception as exc:
            logger.warning("Events unavailable for %s: %s", symbol, exc)
            return []

        weights: list[float] = []
        for event in events:
            sign = _SENTIMENT_SIGN.get(event.sentiment.value, 0.0)
            weight = _IMPORTANCE_WEIGHT.get(event.importance.value, 0.5)
            weights.append(sign * weight)
        return weights

    def _to_view(self, score: CompanyScore) -> CompanyScoreView:
        return CompanyScoreView(
            symbol=score.symbol,
            as_of=score.as_of,
            overall_score=score.overall_score,
            growth_score=score.growth_score,
            risk_score=score.risk_score,
            sentiment_score=score.sentiment_score,
            rating=score.rating.value,
            company_name=score.company_name,
            sector=score.sector,
            market_cap=score.market_cap,
            event_count=score.event_count,
            price_points=score.price_points,
            rationale=score.rationale,
            source=score.source,
        )
