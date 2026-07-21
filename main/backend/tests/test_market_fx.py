from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from backend.modules.market_data.application.dto import (
    HistoricalPriceRequest,
    QuoteRequest,
    SyncHistoricalPricesRequest,
)
from backend.modules.market_data.application.services import MarketDataService
from backend.modules.market_data.domain.entities import HistoricalPriceBar, MarketQuote
from backend.modules.market_data.infrastructure.fx import StaticFxRateProvider
from backend.modules.market_data.infrastructure.repositories import (
    InMemoryCompanyProfileRepository,
    InMemoryHistoricalPriceRepository,
    InMemoryMarketMetadataRepository,
    InMemoryQuoteRepository,
    InMemorySymbolSearchRepository,
)
from backend.shared.types import CurrencyCode, Money, Symbol


class _UsdHistoryProvider:
    async def get_price_history(self, symbol, start_at, end_at):
        usd = CurrencyCode("USD")
        return [
            HistoricalPriceBar(
                symbol=symbol,
                native_currency=usd,
                open_price=Money(amount=Decimal("100"), currency=usd),
                high_price=Money(amount=Decimal("110"), currency=usd),
                low_price=Money(amount=Decimal("90"), currency=usd),
                close_price=Money(amount=Decimal("100"), currency=usd),
                volume=1000,
                timestamp=start_at,
                source="stub",
            )
        ]


def _service_with_fx(usd_rate: float) -> tuple[MarketDataService, InMemoryQuoteRepository]:
    quote_repo = InMemoryQuoteRepository()
    fx = StaticFxRateProvider(base_currency="INR", overrides={"USD": usd_rate})
    service = MarketDataService(
        quote_repository=quote_repo,
        historical_price_repository=InMemoryHistoricalPriceRepository(),
        symbol_search_repository=InMemorySymbolSearchRepository(),
        market_metadata_repository=InMemoryMarketMetadataRepository(),
        historical_price_provider=_UsdHistoryProvider(),
        company_profile_repository=InMemoryCompanyProfileRepository(),
        fx_rate_provider=fx,
        base_currency=CurrencyCode("INR"),
    )
    return service, quote_repo


@pytest.mark.asyncio
async def test_usd_quote_is_converted_to_inr() -> None:
    service, quote_repo = _service_with_fx(usd_rate=80.0)
    usd = CurrencyCode("USD")
    await quote_repo.save_quote(
        MarketQuote(
            symbol=Symbol("AAPL"),
            native_currency=usd,
            last_price=Money(amount=Decimal("100"), currency=usd),
            previous_close=Money(amount=Decimal("100"), currency=usd),
        )
    )

    view = await service.get_quote(QuoteRequest(symbol=Symbol("AAPL")))

    assert view.currency == "INR"
    assert view.last_price == "8000.00"  # 100 USD * 80


@pytest.mark.asyncio
async def test_history_is_stored_and_served_in_inr() -> None:
    service, _ = _service_with_fx(usd_rate=80.0)

    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 1, 2, tzinfo=UTC)
    await service.sync_historical_prices(
        SyncHistoricalPricesRequest(symbol=Symbol("AAPL"), start_at=start, end_at=end)
    )

    series = await service.get_historical_prices(
        HistoricalPriceRequest(
            symbol=Symbol("AAPL"), start_at=start, end_at=end, auto_sync=False
        )
    )

    assert series.currency == "INR"
    assert series.prices[0].close_price == "8000.00"  # 100 USD * 80


@pytest.mark.asyncio
async def test_static_provider_unknown_currency_is_passthrough() -> None:
    fx = StaticFxRateProvider(base_currency="INR")
    # INR -> INR is 1; an unknown currency resolves to 1 (never crashes).
    assert await fx.get_rate_to_base("INR") == Decimal("1")
    assert await fx.get_rate_to_base("ZZZ") == Decimal("1")
