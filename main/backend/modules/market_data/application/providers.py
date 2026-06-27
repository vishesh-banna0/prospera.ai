from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from backend.modules.market_data.domain.entities import CompanyProfile
from backend.modules.market_data.domain.entities import (
    HistoricalPriceBar,
    Instrument,
    MarketMetadata,
    MarketQuote,
)
from backend.shared.types import Symbol
from backend.shared.types import Timestamp


class QuoteProviderContract(ABC):
    """
    Contract for retrieving current market quotes.
    """

    @abstractmethod
    async def get_quote(
        self,
        symbol: Symbol,
    ) -> MarketQuote:
        raise NotImplementedError


class HistoricalPriceProviderContract(ABC):
    """
    Contract for retrieving historical market data.
    """

    @abstractmethod
    async def get_price_history(
        self,
        symbol: Symbol,
        start_at: Timestamp,
        end_at: Timestamp,
    ) -> list[HistoricalPriceBar]:
        raise NotImplementedError


class SymbolSearchProviderContract(ABC):
    """
    Contract for symbol discovery and lookup.
    """

    @abstractmethod
    async def search_symbols(
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


class CompanyProfileProviderContract(ABC):
    """
    Contract for retrieving company metadata from external providers.
    """

    @abstractmethod
    async def get_company_profile(
        self,
        symbol: Symbol,
    ) -> CompanyProfile | None:
        raise NotImplementedError


class MarketMetadataProviderContract(ABC):
    """
    Contract for retrieving market metadata.
    """

    @abstractmethod
    async def get_metadata(
        self,
    ) -> MarketMetadata:
        raise NotImplementedError
# Purpose:
# Declares provider-facing contracts used by the market data service.
#
# Future Responsibilities:
# - Define the interface each external market data adapter must satisfy.
# - Allow provider changes without breaking simulator or API consumers.
# - Support future fallback strategies across multiple vendors.
#
# Dependencies:
# - backend.modules.market_data.domain.entities
#
# Future Classes / Interfaces:
# - MarketDataProvider
# - QuoteProviderContract
# - HistoricalPriceProviderContract
# - SymbolSearchProviderContract
#
# What Should Not Live Here:
# - Concrete HTTP request code.
# - API serialization.
# - Portfolio valuation logic.
