from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from backend.modules.market_data.domain.entities import (
    HistoricalPriceBar,
    Instrument,
    MarketMetadata,
    MarketQuote,
)
from backend.shared.types import Symbol


class QuoteRepository(ABC):

    @abstractmethod
    async def get_quote(
        self,
        symbol: Symbol,
    ) -> MarketQuote:
        raise NotImplementedError


class HistoricalPriceRepository(ABC):

    @abstractmethod
    async def get_price_history(
        self,
        symbol: Symbol,
    ) -> list[HistoricalPriceBar]:
        raise NotImplementedError


class SymbolSearchRepository(ABC):

    @abstractmethod
    async def search(
        self,
        query: str,
    ) -> list[Instrument]:
        raise NotImplementedError

    @abstractmethod
    async def get_instrument(
        self,
        symbol: Symbol,
    ) -> Instrument | None:
        raise NotImplementedError


class MarketMetadataRepository(ABC):

    @abstractmethod
    async def get_metadata(
        self,
    ) -> MarketMetadata:
        raise NotImplementedError
# Purpose:
# Declares contracts required to retrieve and optionally cache market data.
#
# Future Responsibilities:
# - Define how current quotes are retrieved.
# - Define how historical prices are accessed.
# - Define how symbol search and metadata lookup are performed.
#
# Dependencies:
# - backend.modules.market_data.domain.entities
#
# Future Classes / Interfaces:
# - QuoteRepository
# - HistoricalPriceRepository
# - SymbolSearchRepository
# - MarketMetadataRepository
#
# What Should Not Live Here:
# - Provider-specific HTTP code.
# - Simulator read models.
# - API pagination formatting.
