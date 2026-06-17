from __future__ import annotations

from backend.modules.market_data.application.dto import (
    HistoricalPriceRequest,
    HistoricalPriceSeriesView,
    InstrumentSearchResultView,
    InstrumentSearchResultsView,
    MarketMetadataView,
    QuoteRequest,
    QuoteView,
    SymbolSearchRequest,
)
from backend.modules.market_data.domain.repositories import (
    HistoricalPriceRepository,
    MarketMetadataRepository,
    QuoteRepository,
    SymbolSearchRepository,
)


class MarketDataService:
    """
    Application service responsible for exposing market data
    to internal consumers.

    Consumers:
    - Simulator
    - Historical Investment Simulation Engine
    - Backtesting Engine
    - Future AI Agents
    """

    def __init__(
        self,
        quote_repository: QuoteRepository,
        historical_price_repository: HistoricalPriceRepository,
        symbol_search_repository: SymbolSearchRepository,
        market_metadata_repository: MarketMetadataRepository,
    ) -> None:
        self._quote_repository = quote_repository
        self._historical_price_repository = historical_price_repository
        self._symbol_search_repository = symbol_search_repository
        self._market_metadata_repository = market_metadata_repository

    async def get_quote(
        self,
        request: QuoteRequest,
    ) -> QuoteView:
        quote = await self._quote_repository.get_quote(
            request.symbol,
        )

        return QuoteView(
            symbol=quote.symbol,
            currency=quote.native_currency,
            last_price=str(quote.last_price.amount),
            open_price=str(quote.open_price.amount)
            if quote.open_price
            else None,
            high_price=str(quote.high_price.amount)
            if quote.high_price
            else None,
            low_price=str(quote.low_price.amount)
            if quote.low_price
            else None,
            previous_close=str(quote.previous_close.amount)
            if quote.previous_close
            else None,
            volume=quote.volume,
            as_of=quote.as_of,
        )

    async def get_historical_prices(
        self,
        request: HistoricalPriceRequest,
    ) -> HistoricalPriceSeriesView:
        raise NotImplementedError

    async def search_symbols(
        self,
        request: SymbolSearchRequest,
    ) -> InstrumentSearchResultsView:
        instruments = await self._symbol_search_repository.search(
            request.query,
        )

        results = tuple(
            InstrumentSearchResultView(
                symbol=instrument.symbol,
                instrument_name=instrument.instrument_name,
                exchange=instrument.exchange,
                currency=instrument.native_currency,
            )
            for instrument in instruments[: request.limit]
        )

        return InstrumentSearchResultsView(
            results=results,
        )

    async def get_market_metadata(
        self,
    ) -> MarketMetadataView:
        metadata = await self._market_metadata_repository.get_metadata()

        return MarketMetadataView(
            supported_exchanges=metadata.supported_exchanges,
            supported_currencies=metadata.supported_currencies,
            timezone=metadata.timezone,
            market_status=metadata.market_status,
            last_updated_at=metadata.last_updated_at,
        )
# Purpose:
# Placeholder module for market data read services.
#
# Future Responsibilities:
# - Provide current prices to the simulator.
# - Provide historical prices for future backtesting and analysis.
# - Provide symbol search and market metadata to all internal consumers.
# - Apply caching or freshness policies without leaking provider details upward.
#
# Dependencies:
# - backend.modules.market_data.application.dto
# - backend.modules.market_data.domain.repositories
#
# Future Classes / Functions:
# - MarketDataService
# - GetQuoteUseCase
# - GetHistoricalPricesUseCase
# - SearchSymbolsUseCase
# - GetMarketMetadataUseCase
#
# What Should Not Live Here:
# - HTTP route declarations.
# - Simulator mutation workflows.
# - Raw vendor credential management.
