from __future__ import annotations

from dataclasses import dataclass

from backend.shared.types import CurrencyCode
from backend.shared.types import Symbol
from backend.shared.types import Timestamp


# ============================================================
# Requests
# ============================================================


@dataclass(frozen=True, slots=True)
class QuoteRequest:
    symbol: Symbol


@dataclass(frozen=True, slots=True)
class HistoricalPriceRequest:
    symbol: Symbol
    start_at: Timestamp
    end_at: Timestamp
    auto_sync: bool = True


@dataclass(frozen=True, slots=True)
class SyncHistoricalPricesRequest:
    symbol: Symbol
    start_at: Timestamp
    end_at: Timestamp
    asset_type: str = "stock"


@dataclass(frozen=True, slots=True)
class SymbolSearchRequest:
    query: str
    limit: int = 20


# ============================================================
# Responses
# ============================================================


@dataclass(frozen=True, slots=True)
class QuoteView:
    symbol: Symbol
    currency: CurrencyCode

    last_price: str

    open_price: str | None = None
    high_price: str | None = None
    low_price: str | None = None
    previous_close: str | None = None

    volume: int | None = None
    as_of: Timestamp | None = None


@dataclass(frozen=True, slots=True)
class HistoricalPricePointView:
    timestamp: Timestamp

    open_price: str
    high_price: str
    low_price: str
    close_price: str

    volume: int
    adjusted_close_price: str | None = None
    split_coefficient: str | None = None
    dividend_amount: str | None = None


@dataclass(frozen=True, slots=True)
class HistoricalPriceSeriesView:
    symbol: Symbol
    currency: CurrencyCode
    prices: tuple[HistoricalPricePointView, ...]


@dataclass(frozen=True, slots=True)
class SyncHistoricalPricesView:
    symbol: Symbol
    requested_start_at: Timestamp
    requested_end_at: Timestamp
    fetched_count: int
    stored_count: int
    skipped: bool = False
    message: str | None = None


@dataclass(frozen=True, slots=True)
class InstrumentSearchResultView:
    symbol: Symbol
    instrument_name: str
    exchange: str
    currency: CurrencyCode
    asset_type: str = "stock"
    sector: str | None = None
    industry: str | None = None


@dataclass(frozen=True, slots=True)
class InstrumentSearchResultsView:
    results: tuple[InstrumentSearchResultView, ...]


@dataclass(frozen=True, slots=True)
class MarketMetadataView:
    supported_exchanges: tuple[str, ...]
    supported_currencies: tuple[CurrencyCode, ...]

    timezone: str | None = None
    market_status: str | None = None
    last_updated_at: Timestamp | None = None


@dataclass(frozen=True, slots=True)
class CompanyProfileView:
    symbol: Symbol
    instrument_name: str
    currency: CurrencyCode
    exchange: str
    asset_type: str
    sector: str | None = None
    industry: str | None = None
    country: str | None = None
    website: str | None = None
    description: str | None = None
    market_cap: str | None = None
    employees: int | None = None
# Purpose:
# Defines input and output contracts for market data use cases.
#
# Future Responsibilities:
# - Standardize quote requests, historical price requests, and symbol search requests.
# - Standardize response objects returned to simulator and API consumers.
#
# Dependencies:
# - backend.shared.types
#
# Future Classes:
# - QuoteRequest
# - HistoricalPriceRequest
# - SymbolSearchRequest
# - QuoteView
# - HistoricalPriceSeriesView
# - InstrumentSearchResultView
#
# What Should Not Live Here:
# - Vendor payload parsing.
# - Cache invalidation logic.
# - Simulator performance calculations.
