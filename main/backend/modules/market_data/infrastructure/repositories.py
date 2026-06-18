from __future__ import annotations

from backend.modules.market_data.domain.entities import HistoricalPriceBar
from backend.modules.market_data.domain.entities import Instrument
from backend.modules.market_data.domain.entities import MarketMetadata
from backend.modules.market_data.domain.entities import MarketQuote
from backend.modules.market_data.domain.repositories import HistoricalPriceRepository
from backend.modules.market_data.domain.repositories import MarketMetadataRepository
from backend.modules.market_data.domain.repositories import QuoteRepository
from backend.modules.market_data.domain.repositories import SymbolSearchRepository
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