from __future__ import annotations

from datetime import UTC
from datetime import datetime
from decimal import Decimal

import httpx
import pytest

from backend.modules.market_data.domain.entities import Instrument
from backend.modules.market_data.domain.entities import MarketMetadata
from backend.modules.market_data.domain.entities import MarketQuote
from backend.modules.market_data.domain.entities import HistoricalPriceBar
from backend.modules.market_data.domain.entities import CompanyProfile
from backend.modules.market_data.application.dto import (
    HistoricalPriceRequest,
    SyncHistoricalPricesRequest,
)
from backend.modules.market_data.application.services import MarketDataService
from backend.modules.market_data.infrastructure.clients import FinnhubClient
from backend.modules.market_data.infrastructure.repositories import (
    FinnhubMarketMetadataRepository,
    FinnhubQuoteRepository,
    FinnhubSymbolSearchRepository,
    InMemoryCompanyProfileRepository,
    InMemoryHistoricalPriceRepository,
    InMemoryMarketMetadataRepository,
    InMemoryQuoteRepository,
    InMemorySymbolSearchRepository,
)
from backend.shared.types import CurrencyCode
from backend.shared.types import Money
from backend.shared.types import Symbol


class StubSettings:
    market_data_provider = "finnhub"
    market_data_api_key = "test-key"
    market_data_base_url = "https://finnhub.io/api/v1"


class StubHistoricalProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[datetime, datetime]] = []

    async def get_price_history(
        self,
        symbol: Symbol,
        start_at: datetime,
        end_at: datetime,
    ) -> list[HistoricalPriceBar]:
        self.calls.append((start_at, end_at))
        currency = CurrencyCode("USD")
        return [
            HistoricalPriceBar(
                symbol=symbol,
                native_currency=currency,
                open_price=Money(amount=Decimal("100"), currency=currency),
                high_price=Money(amount=Decimal("110"), currency=currency),
                low_price=Money(amount=Decimal("95"), currency=currency),
                close_price=Money(amount=Decimal("105"), currency=currency),
                adjusted_close_price=Money(amount=Decimal("104"), currency=currency),
                volume=1000,
                timestamp=start_at,
                split_coefficient=Decimal("2"),
                source="stub",
            )
        ]


class StubCompanyProfileProvider:
    async def get_company_profile(
        self,
        symbol: Symbol,
    ) -> CompanyProfile:
        return CompanyProfile(
            symbol=symbol,
            instrument_name=f"{symbol} Inc.",
            native_currency=CurrencyCode("USD"),
            exchange="NASDAQ",
            sector="Technology",
            industry="Software",
            source="stub",
            updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


def _build_market_data_service(
    historical_provider: StubHistoricalProvider,
) -> MarketDataService:
    history_repo = InMemoryHistoricalPriceRepository()
    symbol_repo = InMemorySymbolSearchRepository()
    profile_repo = InMemoryCompanyProfileRepository()

    return MarketDataService(
        quote_repository=InMemoryQuoteRepository(),
        historical_price_repository=history_repo,
        symbol_search_repository=symbol_repo,
        market_metadata_repository=InMemoryMarketMetadataRepository(),
        historical_price_provider=historical_provider,
        company_profile_repository=profile_repo,
        company_profile_provider=StubCompanyProfileProvider(),
    )


def test_money_operations_preserve_currency() -> None:
    first = Money(
        amount=Decimal("100.50"),
        currency=CurrencyCode("USD"),
    )
    second = Money(
        amount=Decimal("50.25"),
        currency=CurrencyCode("USD"),
    )

    assert first + second == Money(
        amount=Decimal("150.75"),
        currency=CurrencyCode("USD"),
    )
    assert first - second == Money(
        amount=Decimal("50.25"),
        currency=CurrencyCode("USD"),
    )


def test_instrument_exposes_priced_symbol() -> None:
    instrument = Instrument(
        symbol=Symbol("AAPL"),
        instrument_name="Apple Inc.",
        exchange="NASDAQ",
        native_currency=CurrencyCode("USD"),
    )

    assert instrument.priced_symbol.symbol == Symbol("AAPL")
    assert instrument.priced_symbol.native_currency == CurrencyCode("USD")


def test_market_quote_computes_price_change_percent() -> None:
    quote = MarketQuote(
        symbol=Symbol("AAPL"),
        native_currency=CurrencyCode("USD"),
        last_price=Money(
            amount=Decimal("210"),
            currency=CurrencyCode("USD"),
        ),
        previous_close=Money(
            amount=Decimal("200"),
            currency=CurrencyCode("USD"),
        ),
    )

    assert quote.price_change == Money(
        amount=Decimal("10.00"),
        currency=CurrencyCode("USD"),
    )
    assert quote.price_change_percent == Decimal("5.00")


def test_market_quote_rejects_currency_mismatch() -> None:
    with pytest.raises(ValueError):
        MarketQuote(
            symbol=Symbol("AAPL"),
            native_currency=CurrencyCode("USD"),
            last_price=Money(
                amount=Decimal("210"),
                currency=CurrencyCode("INR"),
            ),
        )


def test_market_metadata_can_be_created() -> None:
    metadata = MarketMetadata(
        supported_exchanges=("NASDAQ", "NYSE"),
        supported_currencies=(CurrencyCode("USD"),),
        timezone="America/New_York",
        market_status="OPEN",
        last_updated_at=datetime(2026, 6, 21, 12, 0, tzinfo=UTC),
    )

    assert metadata.market_status == "OPEN"
    assert metadata.supported_currencies == (CurrencyCode("USD"),)


def _build_mock_client() -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        params = dict(request.url.params)

        if params.get("token") != "test-key":
            return httpx.Response(401, json={"error": "Invalid API key"})

        if path.endswith("/quote") and params.get("symbol") == "AAPL":
            return httpx.Response(
                200,
                json={
                    "c": 212.35,
                    "h": 214.0,
                    "l": 210.75,
                    "o": 211.1,
                    "pc": 209.4,
                    "t": 1718971200,
                },
            )

        if path.endswith("/stock/profile2") and params.get("symbol") == "AAPL":
            return httpx.Response(
                200,
                json={
                    "country": "US",
                    "currency": "USD",
                    "exchange": "NASDAQ",
                    "finnhubIndustry": "Technology",
                    "name": "Apple Inc",
                    "ticker": "AAPL",
                },
            )

        if path.endswith("/search") and params.get("q") == "apple":
            return httpx.Response(
                200,
                json={
                    "count": 1,
                    "result": [
                        {
                            "description": "Apple Inc",
                            "displaySymbol": "AAPL",
                            "symbol": "AAPL",
                            "type": "Common Stock",
                        }
                    ],
                },
            )

        if path.endswith("/stock/market-status") and params.get("exchange") == "US":
            return httpx.Response(
                200,
                json={
                    "exchange": "US",
                    "holiday": None,
                    "isOpen": True,
                    "session": "regular",
                    "timezone": "America/New_York",
                    "t": 1718971200,
                },
            )

        if path.endswith("/stock/symbol"):
            return httpx.Response(
                200,
                json=[{"description": "Apple Inc", "symbol": "AAPL"}],
            )

        return httpx.Response(404, json={"error": f"Unhandled path: {path}"})

    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(
        transport=transport,
        base_url="https://finnhub.io/api/v1",
    )


@pytest.mark.asyncio
async def test_finnhub_quote_repository_normalizes_quote_data() -> None:
    async with _build_mock_client() as http_client:
        repository = FinnhubQuoteRepository(
            FinnhubClient(
                settings=StubSettings(),
                http_client=http_client,
            )
        )

        quote = await repository.get_quote(Symbol("AAPL"))

    assert quote.symbol == Symbol("AAPL")
    assert quote.native_currency == CurrencyCode("USD")
    assert quote.last_price.amount == Decimal("212.35")
    assert quote.open_price is not None
    assert quote.open_price.amount == Decimal("211.10")
    assert quote.previous_close is not None
    assert quote.previous_close.amount == Decimal("209.40")
    assert quote.as_of == datetime.fromtimestamp(1718971200, tz=UTC)


@pytest.mark.asyncio
async def test_finnhub_symbol_search_repository_enriches_results() -> None:
    async with _build_mock_client() as http_client:
        repository = FinnhubSymbolSearchRepository(
            FinnhubClient(
                settings=StubSettings(),
                http_client=http_client,
            )
        )

        instruments = await repository.search("apple")

    assert len(instruments) == 1
    assert instruments[0] == Instrument(
        symbol=Symbol("AAPL"),
        instrument_name="Apple Inc",
        exchange="NASDAQ",
        native_currency=CurrencyCode("USD"),
        industry="Technology",
    )


@pytest.mark.asyncio
async def test_finnhub_market_metadata_repository_normalizes_status() -> None:
    async with _build_mock_client() as http_client:
        repository = FinnhubMarketMetadataRepository(
            FinnhubClient(
                settings=StubSettings(),
                http_client=http_client,
            )
        )

        metadata = await repository.get_metadata()

    assert metadata.supported_exchanges == ("US",)
    assert metadata.supported_currencies == (CurrencyCode("USD"),)
    assert metadata.timezone == "America/New_York"
    assert metadata.market_status == "OPEN"
    assert metadata.last_updated_at == datetime.fromtimestamp(1718971200, tz=UTC)


@pytest.mark.asyncio
async def test_market_data_service_syncs_and_serves_historical_prices() -> None:
    provider = StubHistoricalProvider()
    service = _build_market_data_service(provider)
    start_at = datetime(2026, 1, 2, tzinfo=UTC)
    end_at = datetime(2026, 1, 5, tzinfo=UTC)

    sync_result = await service.sync_historical_prices(
        SyncHistoricalPricesRequest(
            symbol=Symbol("aapl"),
            start_at=start_at,
            end_at=end_at,
        )
    )

    history = await service.get_historical_prices(
        HistoricalPriceRequest(
            symbol=Symbol("AAPL"),
            start_at=start_at,
            end_at=end_at,
            auto_sync=False,
        )
    )

    assert sync_result.symbol == Symbol("AAPL")
    assert sync_result.fetched_count == 1
    assert sync_result.stored_count == 1
    assert len(history.prices) == 1
    assert history.prices[0].adjusted_close_price == "104.00"
    assert history.prices[0].split_coefficient == "2"
    assert history.prices[0].volume == 1000


@pytest.mark.asyncio
async def test_market_data_service_skips_incremental_sync_when_current() -> None:
    provider = StubHistoricalProvider()
    service = _build_market_data_service(provider)
    start_at = datetime(2026, 1, 2, tzinfo=UTC)
    end_at = datetime(2026, 1, 5, tzinfo=UTC)

    await service.sync_historical_prices(
        SyncHistoricalPricesRequest(
            symbol=Symbol("AAPL"),
            start_at=start_at,
            end_at=end_at,
        )
    )
    skipped_result = await service.sync_historical_prices(
        SyncHistoricalPricesRequest(
            symbol=Symbol("AAPL"),
            start_at=start_at,
            end_at=start_at,
        )
    )

    assert len(provider.calls) == 1
    assert skipped_result.skipped is True
    assert skipped_result.fetched_count == 0
