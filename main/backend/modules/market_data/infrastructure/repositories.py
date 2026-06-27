from __future__ import annotations

from datetime import UTC
from datetime import date
from datetime import datetime
from datetime import time
from decimal import Decimal
from typing import Any

from backend.core.exceptions import MarketDataProviderError
from backend.core.exceptions import MarketDataUnavailableError
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.modules.market_data.application.providers import CompanyProfileProviderContract
from backend.modules.market_data.application.providers import HistoricalPriceProviderContract
from backend.modules.market_data.domain.entities import AssetType
from backend.modules.market_data.domain.entities import CompanyProfile
from backend.modules.market_data.domain.entities import HistoricalPriceBar
from backend.modules.market_data.domain.entities import Instrument
from backend.modules.market_data.domain.entities import MarketMetadata
from backend.modules.market_data.domain.entities import MarketQuote
from backend.modules.market_data.domain.repositories import CompanyProfileRepository
from backend.modules.market_data.domain.repositories import HistoricalPriceRepository
from backend.modules.market_data.domain.repositories import MarketMetadataRepository
from backend.modules.market_data.domain.repositories import QuoteRepository
from backend.modules.market_data.domain.repositories import SymbolSearchRepository
from backend.modules.market_data.infrastructure.clients import FinnhubClient
from backend.modules.market_data.infrastructure.clients import YFinanceClient
from backend.modules.market_data.infrastructure.models import CompanyProfileModel
from backend.modules.market_data.infrastructure.models import HistoricalPriceModel
from backend.modules.market_data.infrastructure.models import MarketInstrumentModel
from backend.shared.types import CurrencyCode
from backend.shared.types import Money
from backend.shared.types import Symbol
from backend.shared.types import Timestamp


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
        start_at: Timestamp | None = None,
        end_at: Timestamp | None = None,
    ) -> list[HistoricalPriceBar]:
        bars = self._history.get(symbol, [])
        if start_at is not None:
            bars = [bar for bar in bars if bar.timestamp >= start_at]
        if end_at is not None:
            bars = [bar for bar in bars if bar.timestamp <= end_at]
        return bars

    async def get_latest_price_timestamp(
        self,
        symbol: Symbol,
    ) -> Timestamp | None:
        bars = self._history.get(symbol, [])
        if not bars:
            return None
        return max(bar.timestamp for bar in bars)

    async def save_price_history(
        self,
        symbol: Symbol,
        bars: list[HistoricalPriceBar],
    ) -> None:
        self._history[symbol] = bars

    async def upsert_price_history(
        self,
        bars: list[HistoricalPriceBar],
    ) -> int:
        if not bars:
            return 0

        symbol = bars[0].symbol
        existing = {
            bar.timestamp.date(): bar
            for bar in self._history.get(symbol, [])
        }
        for bar in bars:
            existing[bar.timestamp.date()] = bar
        self._history[symbol] = sorted(
            existing.values(),
            key=lambda bar: bar.timestamp,
        )
        return len(bars)


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

    async def upsert_instrument(
        self,
        instrument: Instrument,
    ) -> None:
        await self.save_instrument(instrument)


class InMemoryCompanyProfileRepository(CompanyProfileRepository):
    """
    Temporary in-memory company profile repository.
    """

    def __init__(self) -> None:
        self._profiles: dict[Symbol, CompanyProfile] = {}

    async def get_company_profile(
        self,
        symbol: Symbol,
    ) -> CompanyProfile | None:
        return self._profiles.get(symbol)

    async def upsert_company_profile(
        self,
        profile: CompanyProfile,
    ) -> None:
        self._profiles[profile.symbol] = profile


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

    async def upsert_instrument(
        self,
        instrument: Instrument,
    ) -> None:
        return None

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


class YFinanceHistoricalDataProvider(
    HistoricalPriceProviderContract,
    CompanyProfileProviderContract,
):
    """
    yfinance provider adapter that emits Prospera domain entities.
    """

    def __init__(
        self,
        client: YFinanceClient | None = None,
    ) -> None:
        self._client = client or YFinanceClient()

    async def get_price_history(
        self,
        symbol: Symbol,
        start_at: Timestamp,
        end_at: Timestamp,
    ) -> list[HistoricalPriceBar]:
        info = await self._client.get_info(str(symbol))
        currency = CurrencyCode(str(info.get("currency") or "USD").upper())
        raw_history = await self._client.get_price_history(
            str(symbol),
            start_at,
            end_at,
        )

        if raw_history is None or getattr(raw_history, "empty", True):
            raise MarketDataUnavailableError(
                f"yfinance returned no historical prices for {symbol}."
            )

        bars: list[HistoricalPriceBar] = []
        for index, row in raw_history.iterrows():
            try:
                bar = self._row_to_bar(
                    symbol=symbol,
                    currency=currency,
                    index=index,
                    row=row,
                )
            except ValueError:
                continue
            bars.append(bar)

        if not bars:
            raise MarketDataUnavailableError(
                f"yfinance returned no usable historical prices for {symbol}."
            )

        return bars

    async def get_company_profile(
        self,
        symbol: Symbol,
    ) -> CompanyProfile | None:
        info = await self._client.get_info(str(symbol))
        if not info:
            return None

        currency = CurrencyCode(str(info.get("currency") or "USD").upper())
        exchange = str(
            info.get("fullExchangeName")
            or info.get("exchange")
            or "UNKNOWN"
        )
        instrument_name = str(
            info.get("longName")
            or info.get("shortName")
            or symbol
        )

        return CompanyProfile(
            symbol=symbol,
            instrument_name=instrument_name,
            native_currency=currency,
            exchange=exchange,
            asset_type=self._asset_type_from_quote_type(info.get("quoteType")),
            sector=self._optional_text(info.get("sector")),
            industry=self._optional_text(info.get("industry")),
            country=self._optional_text(info.get("country")),
            website=self._optional_text(info.get("website")),
            description=self._optional_text(info.get("longBusinessSummary")),
            market_cap=self._optional_decimal(info.get("marketCap")),
            employees=self._optional_int(info.get("fullTimeEmployees")),
            source=self._client.provider_name,
            updated_at=datetime.now(UTC),
        )

    def _row_to_bar(
        self,
        symbol: Symbol,
        currency: CurrencyCode,
        index: Any,
        row: Any,
    ) -> HistoricalPriceBar:
        timestamp = self._timestamp_from_index(index)
        open_price = self._required_money(row.get("Open"), currency)
        high_price = self._required_money(row.get("High"), currency)
        low_price = self._required_money(row.get("Low"), currency)
        close_price = self._required_money(row.get("Close"), currency)

        return HistoricalPriceBar(
            symbol=symbol,
            native_currency=currency,
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            adjusted_close_price=self._optional_money(row.get("Adj Close"), currency),
            volume=max(0, int(row.get("Volume") or 0)),
            timestamp=timestamp,
            split_coefficient=self._optional_non_zero_decimal(row.get("Stock Splits")),
            dividend_amount=self._optional_money(row.get("Dividends"), currency),
            source=self._client.provider_name,
        )

    def _timestamp_from_index(
        self,
        index: Any,
    ) -> Timestamp:
        if hasattr(index, "to_pydatetime"):
            raw_timestamp = index.to_pydatetime()
        elif isinstance(index, datetime):
            raw_timestamp = index
        elif isinstance(index, date):
            raw_timestamp = datetime.combine(index, time.min)
        else:
            raw_timestamp = datetime.fromisoformat(str(index))

        if raw_timestamp.tzinfo is None:
            return raw_timestamp.replace(tzinfo=UTC)

        return raw_timestamp.astimezone(UTC)

    def _required_money(
        self,
        raw_value: Any,
        currency: CurrencyCode,
    ) -> Money:
        decimal_value = self._optional_decimal(raw_value)
        if decimal_value is None:
            raise ValueError("Missing required price value.")
        return Money(amount=decimal_value, currency=currency)

    def _optional_money(
        self,
        raw_value: Any,
        currency: CurrencyCode,
    ) -> Money | None:
        decimal_value = self._optional_non_zero_decimal(raw_value)
        if decimal_value is None:
            return None
        return Money(amount=decimal_value, currency=currency)

    def _optional_non_zero_decimal(
        self,
        raw_value: Any,
    ) -> Decimal | None:
        decimal_value = self._optional_decimal(raw_value)
        if decimal_value is None or decimal_value == Decimal("0"):
            return None
        return decimal_value

    def _optional_decimal(
        self,
        raw_value: Any,
    ) -> Decimal | None:
        if raw_value in (None, ""):
            return None

        try:
            decimal_value = Decimal(str(raw_value))
        except Exception as exc:
            raise ValueError("Invalid decimal value.") from exc

        if decimal_value.is_nan():
            return None

        return decimal_value

    def _optional_int(
        self,
        raw_value: Any,
    ) -> int | None:
        if raw_value in (None, ""):
            return None
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return None

    def _optional_text(
        self,
        raw_value: Any,
    ) -> str | None:
        if raw_value in (None, ""):
            return None
        return str(raw_value)

    def _asset_type_from_quote_type(
        self,
        raw_quote_type: Any,
    ) -> AssetType:
        quote_type = str(raw_quote_type or "").upper()
        if quote_type == "INDEX":
            return AssetType.INDEX
        if quote_type in {"MUTUALFUND", "MUTUAL_FUND"}:
            return AssetType.MUTUAL_FUND
        return AssetType.STOCK


class SqlMarketDataRepository(
    HistoricalPriceRepository,
    SymbolSearchRepository,
    CompanyProfileRepository,
):
    """
    PostgreSQL-backed market data repository.
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def get_price_history(
        self,
        symbol: Symbol,
        start_at: Timestamp | None = None,
        end_at: Timestamp | None = None,
    ) -> list[HistoricalPriceBar]:
        stmt = select(HistoricalPriceModel).where(
            HistoricalPriceModel.symbol == str(symbol)
        )

        if start_at is not None:
            stmt = stmt.where(HistoricalPriceModel.price_date >= start_at.date())
        if end_at is not None:
            stmt = stmt.where(HistoricalPriceModel.price_date <= end_at.date())

        stmt = stmt.order_by(HistoricalPriceModel.price_date.asc())
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        instrument = await self.get_instrument(symbol)
        currency = (
            instrument.native_currency
            if instrument is not None
            else CurrencyCode("USD")
        )

        return [self._price_model_to_entity(model, currency) for model in models]

    async def get_latest_price_timestamp(
        self,
        symbol: Symbol,
    ) -> Timestamp | None:
        stmt = (
            select(HistoricalPriceModel)
            .where(HistoricalPriceModel.symbol == str(symbol))
            .order_by(HistoricalPriceModel.price_date.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None

        return datetime.combine(model.price_date, time.min, tzinfo=UTC)

    async def upsert_price_history(
        self,
        bars: list[HistoricalPriceBar],
    ) -> int:
        if not bars:
            return 0

        for bar in bars:
            stmt = select(HistoricalPriceModel).where(
                HistoricalPriceModel.symbol == str(bar.symbol),
                HistoricalPriceModel.price_date == bar.timestamp.date(),
            )
            result = await self._session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                self._session.add(self._price_entity_to_model(bar))
                continue

            model.open_price = bar.open_price.amount
            model.high_price = bar.high_price.amount
            model.low_price = bar.low_price.amount
            model.close_price = bar.close_price.amount
            model.adjusted_close_price = (
                bar.adjusted_close_price.amount
                if bar.adjusted_close_price is not None
                else None
            )
            model.volume = bar.volume
            model.split_coefficient = bar.split_coefficient
            model.dividend_amount = (
                bar.dividend_amount.amount
                if bar.dividend_amount is not None
                else None
            )
            model.source = bar.source
            model.updated_at = datetime.now(UTC)

        await self._session.flush()
        return len(bars)

    async def search(
        self,
        query: str,
    ) -> list[Instrument]:
        query_text = f"%{query.strip()}%"
        stmt = (
            select(MarketInstrumentModel)
            .where(
                or_(
                    MarketInstrumentModel.symbol.ilike(query_text),
                    MarketInstrumentModel.instrument_name.ilike(query_text),
                    MarketInstrumentModel.sector.ilike(query_text),
                    MarketInstrumentModel.industry.ilike(query_text),
                )
            )
            .order_by(MarketInstrumentModel.symbol.asc())
            .limit(50)
        )
        result = await self._session.execute(stmt)
        return [
            self._instrument_model_to_entity(model)
            for model in result.scalars().all()
        ]

    async def get_instrument(
        self,
        symbol: Symbol,
    ) -> Instrument | None:
        stmt = select(MarketInstrumentModel).where(
            MarketInstrumentModel.symbol == str(symbol)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._instrument_model_to_entity(model)

    async def upsert_instrument(
        self,
        instrument: Instrument,
    ) -> None:
        stmt = select(MarketInstrumentModel).where(
            MarketInstrumentModel.symbol == str(instrument.symbol)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        now = datetime.now(UTC)

        if model is None:
            self._session.add(
                MarketInstrumentModel(
                    symbol=str(instrument.symbol),
                    instrument_name=instrument.instrument_name,
                    exchange=instrument.exchange,
                    native_currency=str(instrument.native_currency),
                    asset_type=instrument.asset_type.value,
                    isin=instrument.isin,
                    sector=instrument.sector,
                    industry=instrument.industry,
                    country=instrument.country,
                    provider_symbol=instrument.provider_symbol,
                    is_active=instrument.is_active,
                    created_at=now,
                )
            )
        else:
            model.instrument_name = instrument.instrument_name
            model.exchange = instrument.exchange
            model.native_currency = str(instrument.native_currency)
            model.asset_type = instrument.asset_type.value
            model.isin = instrument.isin
            model.sector = instrument.sector
            model.industry = instrument.industry
            model.country = instrument.country
            model.provider_symbol = instrument.provider_symbol
            model.is_active = instrument.is_active
            model.updated_at = now

        await self._session.flush()

    async def get_company_profile(
        self,
        symbol: Symbol,
    ) -> CompanyProfile | None:
        stmt = select(CompanyProfileModel).where(
            CompanyProfileModel.symbol == str(symbol)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._company_model_to_entity(model)

    async def upsert_company_profile(
        self,
        profile: CompanyProfile,
    ) -> None:
        stmt = select(CompanyProfileModel).where(
            CompanyProfileModel.symbol == str(profile.symbol)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        now = profile.updated_at or datetime.now(UTC)

        if model is None:
            self._session.add(
                CompanyProfileModel(
                    symbol=str(profile.symbol),
                    instrument_name=profile.instrument_name,
                    native_currency=str(profile.native_currency),
                    exchange=profile.exchange,
                    asset_type=profile.asset_type.value,
                    sector=profile.sector,
                    industry=profile.industry,
                    country=profile.country,
                    website=profile.website,
                    description=profile.description,
                    market_cap=profile.market_cap,
                    employees=profile.employees,
                    source=profile.source,
                    updated_at=now,
                )
            )
        else:
            model.instrument_name = profile.instrument_name
            model.native_currency = str(profile.native_currency)
            model.exchange = profile.exchange
            model.asset_type = profile.asset_type.value
            model.sector = profile.sector
            model.industry = profile.industry
            model.country = profile.country
            model.website = profile.website
            model.description = profile.description
            model.market_cap = profile.market_cap
            model.employees = profile.employees
            model.source = profile.source
            model.updated_at = now

        await self._session.flush()

    def _price_entity_to_model(
        self,
        bar: HistoricalPriceBar,
    ) -> HistoricalPriceModel:
        now = datetime.now(UTC)
        return HistoricalPriceModel(
            symbol=str(bar.symbol),
            price_date=bar.timestamp.date(),
            open_price=bar.open_price.amount,
            high_price=bar.high_price.amount,
            low_price=bar.low_price.amount,
            close_price=bar.close_price.amount,
            adjusted_close_price=(
                bar.adjusted_close_price.amount
                if bar.adjusted_close_price is not None
                else None
            ),
            volume=bar.volume,
            split_coefficient=bar.split_coefficient,
            dividend_amount=(
                bar.dividend_amount.amount
                if bar.dividend_amount is not None
                else None
            ),
            source=bar.source,
            created_at=now,
        )

    def _price_model_to_entity(
        self,
        model: HistoricalPriceModel,
        currency: CurrencyCode,
    ) -> HistoricalPriceBar:
        timestamp = datetime.combine(model.price_date, time.min, tzinfo=UTC)

        return HistoricalPriceBar(
            symbol=Symbol(model.symbol),
            native_currency=currency,
            open_price=Money(amount=model.open_price, currency=currency),
            high_price=Money(amount=model.high_price, currency=currency),
            low_price=Money(amount=model.low_price, currency=currency),
            close_price=Money(amount=model.close_price, currency=currency),
            adjusted_close_price=(
                Money(amount=model.adjusted_close_price, currency=currency)
                if model.adjusted_close_price is not None
                else None
            ),
            volume=model.volume,
            timestamp=timestamp,
            split_coefficient=model.split_coefficient,
            dividend_amount=(
                Money(amount=model.dividend_amount, currency=currency)
                if model.dividend_amount is not None
                else None
            ),
            source=model.source,
        )

    def _instrument_model_to_entity(
        self,
        model: MarketInstrumentModel,
    ) -> Instrument:
        return Instrument(
            symbol=Symbol(model.symbol),
            instrument_name=model.instrument_name,
            exchange=model.exchange,
            native_currency=CurrencyCode(model.native_currency),
            asset_type=AssetType(model.asset_type),
            isin=model.isin,
            sector=model.sector,
            industry=model.industry,
            country=model.country,
            provider_symbol=model.provider_symbol,
            is_active=model.is_active,
        )

    def _company_model_to_entity(
        self,
        model: CompanyProfileModel,
    ) -> CompanyProfile:
        return CompanyProfile(
            symbol=Symbol(model.symbol),
            instrument_name=model.instrument_name,
            native_currency=CurrencyCode(model.native_currency),
            exchange=model.exchange,
            asset_type=AssetType(model.asset_type),
            sector=model.sector,
            industry=model.industry,
            country=model.country,
            website=model.website,
            description=model.description,
            market_cap=model.market_cap,
            employees=model.employees,
            source=model.source,
            updated_at=model.updated_at,
        )


class CompositeSymbolSearchRepository(SymbolSearchRepository):
    """
    Search local instruments first, then fall back to a provider-backed lookup.
    """

    def __init__(
        self,
        storage_repository: SymbolSearchRepository,
        provider_repository: SymbolSearchRepository,
    ) -> None:
        self._storage_repository = storage_repository
        self._provider_repository = provider_repository

    async def search(
        self,
        query: str,
    ) -> list[Instrument]:
        local_results = await self._storage_repository.search(query)
        if local_results:
            return local_results

        provider_results = await self._provider_repository.search(query)
        for instrument in provider_results:
            await self._storage_repository.upsert_instrument(instrument)
        return provider_results

    async def get_instrument(
        self,
        symbol: Symbol,
    ) -> Instrument | None:
        instrument = await self._storage_repository.get_instrument(symbol)
        if instrument is not None:
            return instrument

        instrument = await self._provider_repository.get_instrument(symbol)
        if instrument is not None:
            await self._storage_repository.upsert_instrument(instrument)
        return instrument

    async def upsert_instrument(
        self,
        instrument: Instrument,
    ) -> None:
        await self._storage_repository.upsert_instrument(instrument)
