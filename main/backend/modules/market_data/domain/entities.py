from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum

from backend.shared.types import CurrencyCode
from backend.shared.types import Money
from backend.shared.types import PricedSymbol
from backend.shared.types import Symbol
from backend.shared.types import Timestamp


class AssetType(StrEnum):
    STOCK = "stock"
    INDEX = "index"
    MUTUAL_FUND = "mutual_fund"


@dataclass(frozen=True, slots=True)
class Instrument:
    symbol: Symbol # ticker symbol, e.g., "AAPL" for Apple Inc.
    instrument_name: str # full name of the instrument, e.g., "Apple Inc."
    exchange: str # exchange where the instrument is listed, e.g., "NASDAQ", "SEBI"
    native_currency: CurrencyCode # the currency in which the instrument is traded, e.g., "USD", "INR"
    asset_type: AssetType = AssetType.STOCK
    isin: str | None = None 
    # International Securities Identification Number, a unique identifier for the instrument
    sector: str | None = None # the sector to which the instrument belongs, e.g., "Technology", "Finance"
    industry: str | None = None # the industry to which the instrument belongs, e.g., "Software", "Banking"
    country: str | None = None
    provider_symbol: str | None = None
    is_active: bool = True # indicates whether the instrument is currently active and tradable

    @property
    def priced_symbol(self) -> PricedSymbol:
        return PricedSymbol(symbol=self.symbol, native_currency=self.native_currency)


@dataclass(frozen=True, slots=True)
class MarketQuote:
    symbol: Symbol # ticker symbol, e.g., "AAPL" for Apple Inc.
    native_currency: CurrencyCode # the currency in which the instrument is traded, e.g., "USD", "INR"
    last_price: Money # the most recent trading price of the instrument
    open_price: Money | None = None # the opening price of the instrument for the current trading session
    high_price: Money | None = None # the highest price of the instrument for the current trading session
    low_price: Money | None = None # the lowest price of the instrument for the current trading session
    previous_close: Money | None = None # the closing price of the instrument from the previous trading session
    volume: int | None = None
    # the total number of shares or contracts traded for the instrument during the current trading session
    as_of: Timestamp | None = None # the timestamp indicating when the quote was last updated or retrieved

    def __post_init__(self) -> None:
        self._assert_money_currency(self.last_price)
        self._assert_optional_money_currency(self.open_price)
        self._assert_optional_money_currency(self.high_price)
        self._assert_optional_money_currency(self.low_price)
        self._assert_optional_money_currency(self.previous_close)

    @property
    def price_change(self) -> Money | None:
        if self.previous_close is None:
            return None
        return self.last_price - self.previous_close

    @property
    def price_change_percent(self) -> Decimal | None:
        if self.previous_close is None or self.previous_close.is_zero():
            return None
        return ((self.last_price.amount - self.previous_close.amount) / self.previous_close.amount) * Decimal("100")

    def _assert_money_currency(self, money: Money) -> None:
        if money.currency != self.native_currency:
            raise ValueError("Quote money currency must match the instrument native currency.")

    def _assert_optional_money_currency(self, money: Money | None) -> None:
        if money is not None:
            self._assert_money_currency(money)


@dataclass(frozen=True, slots=True)
class HistoricalPriceBar:
    symbol: Symbol
    native_currency: CurrencyCode
    open_price: Money
    high_price: Money
    low_price: Money
    close_price: Money
    volume: int
    timestamp: Timestamp
    adjusted_close_price: Money | None = None
    split_coefficient: Decimal | None = None
    dividend_amount: Money | None = None
    source: str | None = None

    def __post_init__(self) -> None:
        self._assert_money_currency(self.open_price)
        self._assert_money_currency(self.high_price)
        self._assert_money_currency(self.low_price)
        self._assert_money_currency(self.close_price)
        self._assert_optional_money_currency(self.adjusted_close_price)
        self._assert_optional_money_currency(self.dividend_amount)
        self._assert_valid_market_bar()

    def _assert_money_currency(self, money: Money) -> None:
        if money.currency != self.native_currency:
            raise ValueError("Historical price money currency must match the instrument native currency.")

    def _assert_optional_money_currency(self, money: Money | None) -> None:
        if money is not None:
            self._assert_money_currency(money)

    def _assert_valid_market_bar(self) -> None:
        if self.volume < 0:
            raise ValueError("Historical price volume cannot be negative.")

        prices = (
            self.open_price.amount,
            self.high_price.amount,
            self.low_price.amount,
            self.close_price.amount,
        )
        if any(price < Decimal("0") for price in prices):
            raise ValueError("Historical prices cannot be negative.")

        if self.high_price.amount < self.low_price.amount:
            raise ValueError("Historical price high cannot be below low.")

        if self.split_coefficient is not None and self.split_coefficient < Decimal("0"):
            raise ValueError("Split coefficient cannot be negative.")


@dataclass(frozen=True, slots=True)
class CompanyProfile:
    symbol: Symbol
    instrument_name: str
    native_currency: CurrencyCode
    exchange: str
    asset_type: AssetType = AssetType.STOCK
    sector: str | None = None
    industry: str | None = None
    country: str | None = None
    website: str | None = None
    description: str | None = None
    market_cap: Decimal | None = None
    employees: int | None = None
    source: str | None = None
    updated_at: Timestamp | None = None


@dataclass(frozen=True, slots=True)
class MutualFundNavRecord:
    """
    Provider-independent placeholder for future mutual fund NAV ingestion.
    """

    scheme_code: str
    scheme_name: str
    native_currency: CurrencyCode
    nav: Money
    timestamp: Timestamp
    source: str | None = None


@dataclass(frozen=True, slots=True)
class MarketMetadata:
    supported_exchanges: tuple[str, ...] = field(default_factory=tuple)
    supported_currencies: tuple[CurrencyCode, ...] = field(default_factory=tuple)
    timezone: str | None = None
    market_status: str | None = None
    last_updated_at: Timestamp | None = None

# Purpose:
# Placeholder definitions for market data domain entities.
#
# Future Responsibilities:
# - Represent tradable instruments and symbol metadata.
# - Represent current quotes consumed by simulator environments.
# - Represent historical price bars for future backtesting and analytics.
#
# Dependencies:
# - backend.shared.types
#
# Future Classes:
# - Instrument
# - MarketQuote
# - HistoricalPriceBar
# - MarketMetadata
#
# Future Fields:
# - symbol
# - exchange
# - instrument_name
# - last_price
# - currency
# - open_price
# - high_price
# - low_price
# - close_price
# - volume
# - as_of
#
# What Should Not Live Here:
# - HTTP response shapes.
# - Vendor response parsing details.
# - Trading policy logic.
