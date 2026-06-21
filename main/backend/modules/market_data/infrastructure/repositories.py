from __future__ import annotations

from datetime import UTC
from datetime import datetime
from decimal import Decimal

from backend.core.exceptions import MarketDataProviderError
from backend.core.exceptions import MarketDataUnavailableError
from backend.modules.market_data.domain.entities import HistoricalPriceBar
from backend.modules.market_data.domain.entities import Instrument
from backend.modules.market_data.domain.entities import MarketMetadata
from backend.modules.market_data.domain.entities import MarketQuote
from backend.modules.market_data.domain.repositories import HistoricalPriceRepository
from backend.modules.market_data.domain.repositories import MarketMetadataRepository
from backend.modules.market_data.domain.repositories import QuoteRepository
from backend.modules.market_data.domain.repositories import SymbolSearchRepository
from backend.modules.market_data.infrastructure.clients import FinnhubClient
from backend.shared.types import CurrencyCode
from backend.shared.types import Money
from backend.shared.types import Symbol


class InMemoryQuoteRepository(QuoteRepository):
    """
    Temporary in-memory implementation.

    Replace with Redis/database-backed caching later.
    """

    def __init__(self) -> None:
        self._quotes: dict[Symbol, MarketQuote] = {}

    async def get_quote(
        self,
        symbol: Symbol,
    ) -> MarketQuote | None:
        return self._quotes.get(symbol)

    async def save_quote(
        self,
        quote: MarketQuote,
    ) -> None:
        self._quotes[quote.symbol] = quote


class InMemoryHistoricalPriceRepository(HistoricalPriceRepository):
    """
    Temporary historical price repository.
    """

    def __init__(self) -> None:
        self._history: dict[Symbol, list[HistoricalPriceBar]] = {}

    async def get_price_history(
        self,
        symbol: Symbol,
    ) -> list[HistoricalPriceBar]:
        return self._history.get(symbol, [])

    async def save_price_history(
        self,
        symbol: Symbol,
        bars: list[HistoricalPriceBar],
    ) -> None:
        self._history[symbol] = bars


class InMemorySymbolSearchRepository(SymbolSearchRepository):
    """
    Temporary instrument repository.
    """

    def __init__(self) -> None:
        self._instruments: dict[Symbol, Instrument] = {}

    async def search(
        self,
        query: str,
    ) -> list[Instrument]:
        query = query.lower()

        return [
            instrument
            for instrument in self._instruments.values()
            if query in instrument.symbol.lower()
            or query in instrument.instrument_name.lower()
        ]

    async def save_instrument(
        self,
        instrument: Instrument,
    ) -> None:
        self._instruments[instrument.symbol] = instrument

    async def get_instrument(
        self,
        symbol: Symbol,
    ) -> Instrument | None:
        return self._instruments.get(symbol)


class InMemoryMarketMetadataRepository(MarketMetadataRepository):
    """
    Temporary metadata repository.
    """

    def __init__(self) -> None:
        self._metadata: MarketMetadata | None = None

    async def get_metadata(
        self,
    ) -> MarketMetadata | None:
        return self._metadata

    async def save_metadata(
        self,
        metadata: MarketMetadata,
    ) -> None:
        self._metadata = metadata


class FinnhubQuoteRepository(QuoteRepository):
    def __init__(
        self,
        client: FinnhubClient,
    ) -> None:
        self._client = client

    async def get_quote(
        self,
        symbol: Symbol,
    ) -> MarketQuote:
        profile = await self._client.get_company_profile(symbol)
        quote = await self._client.get_quote(symbol)

        currency = CurrencyCode(
            str(profile.get("currency") or "USD").upper()
        )

        current_price = self._require_decimal(
            quote.get("c"),
            field_name="c",
            symbol=symbol,
        )

        return MarketQuote(
            symbol=symbol,
            native_currency=currency,
            last_price=Money(amount=current_price, currency=currency),
            open_price=self._optional_money(quote.get("o"), currency),
            high_price=self._optional_money(quote.get("h"), currency),
            low_price=self._optional_money(quote.get("l"), currency),
            previous_close=self._optional_money(quote.get("pc"), currency),
            volume=None,
            as_of=self._optional_timestamp(quote.get("t")),
        )

    def _optional_money(
        self,
        raw_value: object,
        currency: CurrencyCode,
    ) -> Money | None:
        decimal_value = self._optional_decimal(raw_value)
        if decimal_value is None:
            return None

        return Money(amount=decimal_value, currency=currency)

    def _optional_decimal(
        self,
        raw_value: object,
    ) -> Decimal | None:
        if raw_value in (None, ""):
            return None

        decimal_value = Decimal(str(raw_value))
        if decimal_value <= Decimal("0"):
            return None

        return decimal_value

    def _require_decimal(
        self,
        raw_value: object,
        field_name: str,
        symbol: Symbol,
    ) -> Decimal:
        decimal_value = self._optional_decimal(raw_value)
        if decimal_value is None:
            raise MarketDataUnavailableError(
                f"Finnhub did not return a usable {field_name} value for {symbol}."
            )

        return decimal_value

    def _optional_timestamp(
        self,
        raw_value: object,
    ) -> datetime | None:
        if raw_value in (None, "", 0, "0"):
            return None

        try:
            return datetime.fromtimestamp(int(raw_value), tz=UTC)
        except (TypeError, ValueError, OSError) as exc:
            raise MarketDataProviderError(
                "Finnhub returned an invalid quote timestamp."
            ) from exc


class FinnhubSymbolSearchRepository(SymbolSearchRepository):
    def __init__(
        self,
        client: FinnhubClient,
        enrichment_limit: int = 10,
    ) -> None:
        self._client = client
        self._enrichment_limit = enrichment_limit

    async def search(
        self,
        query: str,
    ) -> list[Instrument]:
        results = await self._client.search_symbols(query)
        instruments: list[Instrument] = []

        for item in results[: self._enrichment_limit]:
            symbol = str(item.get("symbol") or item.get("displaySymbol") or "").strip()
            if not symbol:
                continue

            try:
                profile = await self._client.get_company_profile(symbol)
            except (MarketDataProviderError, MarketDataUnavailableError):
                profile = {}

            instruments.append(
                self._build_instrument(
                    symbol=symbol,
                    fallback_name=str(item.get("description") or symbol),
                    fallback_exchange=str(
                        item.get("mic")
                        or item.get("type")
                        or "UNKNOWN"
                    ),
                    profile=profile,
                )
            )

        return instruments

    async def get_instrument(
        self,
        symbol: Symbol,
    ) -> Instrument | None:
        profile = await self._client.get_company_profile(symbol)
        if not profile:
            return None

        return self._build_instrument(
            symbol=str(symbol),
            fallback_name=str(symbol),
            fallback_exchange="UNKNOWN",
            profile=profile,
        )

    def _build_instrument(
        self,
        symbol: str,
        fallback_name: str,
        fallback_exchange: str,
        profile: dict[str, object],
    ) -> Instrument:
        currency = str(profile.get("currency") or "USD").upper()
        exchange = str(profile.get("exchange") or fallback_exchange or "UNKNOWN")
        instrument_name = str(profile.get("name") or fallback_name or symbol)
        industry = profile.get("finnhubIndustry")

        return Instrument(
            symbol=Symbol(symbol),
            instrument_name=instrument_name,
            exchange=exchange,
            native_currency=CurrencyCode(currency),
            industry=str(industry) if industry else None,
        )


class FinnhubMarketMetadataRepository(MarketMetadataRepository):
    def __init__(
        self,
        client: FinnhubClient,
    ) -> None:
        self._client = client

    async def get_metadata(
        self,
    ) -> MarketMetadata:
        status = await self._client.get_market_status()

        is_open = status.get("isOpen")
        market_status = None
        if isinstance(is_open, bool):
            market_status = "OPEN" if is_open else "CLOSED"

        last_updated_at = None
        raw_timestamp = status.get("t")
        if raw_timestamp not in (None, "", 0, "0"):
            last_updated_at = datetime.fromtimestamp(int(raw_timestamp), tz=UTC)

        return MarketMetadata(
            supported_exchanges=("US",),
            supported_currencies=(CurrencyCode("USD"),),
            timezone=str(status.get("timezone") or "America/New_York"),
            market_status=market_status,
            last_updated_at=last_updated_at,
        )
