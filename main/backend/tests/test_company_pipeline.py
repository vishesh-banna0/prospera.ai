from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.modules.company.application.dto import AnalyzeCompanyRequest
from backend.modules.company.application.services import CompanyIntelligenceService
from backend.modules.company.domain.entities import CompanyRating
from backend.modules.company.domain.scoring import (
    annualized_volatility_pct,
    max_drawdown_pct,
    score_company,
    sentiment_score,
    total_return_pct,
)
from backend.modules.company.infrastructure.repositories import (
    InMemoryCompanyScoreRepository,
)
from backend.modules.events.domain.entities import (
    EventImportance,
    EventType,
    NewsEvent,
    Sentiment,
)
from backend.modules.events.infrastructure.repositories import (
    InMemoryNewsEventRepository,
)
from backend.modules.market_data.application.dto import (
    CompanyProfileView,
    HistoricalPricePointView,
    HistoricalPriceSeriesView,
)


# ---- pure scoring math -----------------------------------------------------


def test_total_return_and_volatility_and_drawdown() -> None:
    rising = [100.0, 110.0, 121.0]
    assert total_return_pct(rising) == pytest.approx(21.0)
    assert max_drawdown_pct(rising) == pytest.approx(0.0)

    dip = [100.0, 80.0, 90.0]
    assert max_drawdown_pct(dip) == pytest.approx(20.0)
    assert annualized_volatility_pct([0.01, -0.01, 0.02, -0.02]) > 0.0


def test_sentiment_score_direction() -> None:
    assert sentiment_score([]) == pytest.approx(50.0)  # no news -> neutral
    assert sentiment_score([1.0, 1.0]) > 60.0
    assert sentiment_score([-1.0, -1.0]) < 40.0


def test_score_company_rewards_growth_penalizes_risk() -> None:
    steady_up = [100.0 + i for i in range(60)]  # smooth uptrend, low vol
    score = score_company(
        symbol="AAA",
        as_of=datetime.now(UTC),
        closes=steady_up,
        event_weights=[1.0],
    )
    assert score.growth_score > 60.0
    assert score.rating in (CompanyRating.STRONG, CompanyRating.MODERATE)
    assert 0.0 <= score.overall_score <= 100.0
    assert score.price_points == 60


# ---- service pipeline (offline stubs) --------------------------------------


class StubMarketData:
    def __init__(self, closes: list[float]) -> None:
        self._closes = closes

    async def get_company_profile(self, symbol):
        return CompanyProfileView(
            symbol=symbol,
            instrument_name=f"{symbol} Inc.",
            currency="INR",
            exchange="NASDAQ",
            asset_type="stock",
            sector="Technology",
            market_cap="1000000",
        )

    async def get_historical_prices(self, request):
        prices = tuple(
            HistoricalPricePointView(
                timestamp=datetime(2026, 1, 1, tzinfo=UTC),
                open_price=str(c),
                high_price=str(c),
                low_price=str(c),
                close_price=str(c),
                volume=1000,
            )
            for c in self._closes
        )
        return HistoricalPriceSeriesView(symbol=request.symbol, currency="INR", prices=prices)


@pytest.mark.asyncio
async def test_company_service_analyze_and_retrieve() -> None:
    events = InMemoryNewsEventRepository()
    await events.upsert_events(
        [
            NewsEvent(
                event_id="e1",
                article_id="a1",
                event_type=EventType.EARNINGS_BEAT,
                sentiment=Sentiment.POSITIVE,
                importance=EventImportance.HIGH,
                headline="AAA beats earnings",
                event_date=datetime(2026, 6, 1, tzinfo=UTC),
                symbols=("AAA",),
            )
        ]
    )
    repo = InMemoryCompanyScoreRepository()
    service = CompanyIntelligenceService(
        market_data_service=StubMarketData([100.0 + i for i in range(40)]),
        event_repository=events,
        score_repository=repo,
    )

    view = await service.analyze(AnalyzeCompanyRequest(symbol="aaa", lookback_days=90))
    assert view.symbol == "AAA"
    assert view.company_name == "AAA Inc."
    assert view.sentiment_score > 50.0  # a positive high-importance event
    assert view.event_count == 1
    assert view.price_points == 40

    fetched = await service.get_company("AAA")
    assert fetched.symbol == "AAA"

    listed = await service.list_companies()
    assert listed.count == 1


@pytest.mark.asyncio
async def test_company_service_survives_missing_market_data() -> None:
    class FailingMarketData:
        async def get_company_profile(self, symbol):
            raise RuntimeError("no api key")

        async def get_historical_prices(self, request):
            raise RuntimeError("no api key")

    service = CompanyIntelligenceService(
        market_data_service=FailingMarketData(),
        event_repository=InMemoryNewsEventRepository(),
        score_repository=InMemoryCompanyScoreRepository(),
    )

    # Even with no market data and no events, a neutral scorecard is produced.
    view = await service.analyze(AnalyzeCompanyRequest(symbol="ZZZ"))
    assert view.symbol == "ZZZ"
    assert view.price_points == 0
    assert view.sentiment_score == pytest.approx(50.0)
