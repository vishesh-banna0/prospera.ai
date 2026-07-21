from __future__ import annotations

import logging
from collections.abc import Awaitable
from collections.abc import Callable
from datetime import timedelta

from backend.modules.market_data.application.dto import (
    CompanyProfileView,
    HistoricalPriceRequest,
    HistoricalPricePointView,
    HistoricalPriceSeriesView,
    InstrumentSearchResultView,
    InstrumentSearchResultsView,
    MarketMetadataView,
    QuoteRequest,
    QuoteView,
    SyncHistoricalPricesRequest,
    SyncHistoricalPricesView,
    SymbolSearchRequest,
)
from backend.modules.market_data.application.providers import CompanyProfileProviderContract
from backend.modules.market_data.application.providers import FxRateProviderContract
from backend.modules.market_data.application.providers import HistoricalPriceProviderContract
from backend.modules.market_data.domain.entities import AssetType
from backend.modules.market_data.domain.entities import CompanyProfile
from backend.modules.market_data.domain.entities import HistoricalPriceBar
from backend.modules.market_data.domain.entities import Instrument
from backend.modules.market_data.domain.repositories import CompanyProfileRepository
from backend.modules.market_data.domain.repositories import (
    HistoricalPriceRepository,
    MarketMetadataRepository,
    QuoteRepository,
    SymbolSearchRepository,
)
from backend.shared.types import CurrencyCode
from backend.shared.types import Money
from backend.shared.types import Symbol


logger = logging.getLogger(__name__)


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
        historical_price_provider: HistoricalPriceProviderContract | None = None,
        company_profile_repository: CompanyProfileRepository | None = None,
        company_profile_provider: CompanyProfileProviderContract | None = None,
        fx_rate_provider: FxRateProviderContract | None = None,
        base_currency: CurrencyCode = CurrencyCode("INR"),
        commit: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self._quote_repository = quote_repository
        self._historical_price_repository = historical_price_repository
        self._symbol_search_repository = symbol_search_repository
        self._market_metadata_repository = market_metadata_repository
        self._historical_price_provider = historical_price_provider
        self._company_profile_repository = company_profile_repository
        self._company_profile_provider = company_profile_provider
        self._fx_rate_provider = fx_rate_provider
        self._base_currency = CurrencyCode(str(base_currency).upper())
        self._commit = commit

    async def _to_base_money(self, money: Money | None) -> Money | None:
        """Convert a native-currency Money into the base currency (INR).

        No-op when no FX provider is configured or the amount is already in the
        base currency, so callers can convert unconditionally.
        """

        if money is None:
            return None
        if self._fx_rate_provider is None:
            return money
        if str(money.currency).upper() == str(self._base_currency).upper():
            return Money(amount=money.amount, currency=self._base_currency)
        rate = await self._fx_rate_provider.get_rate_to_base(money.currency)
        return Money(amount=money.amount * rate, currency=self._base_currency)

    async def _convert_bar_to_base(self, bar: HistoricalPriceBar) -> HistoricalPriceBar:
        """Return a copy of ``bar`` with every price converted into the base
        currency. Used at ingestion so the warehouse stores INR."""

        if (
            self._fx_rate_provider is None
            or str(bar.native_currency).upper() == str(self._base_currency).upper()
        ):
            return bar

        rate = await self._fx_rate_provider.get_rate_to_base(bar.native_currency)

        def scale(money: Money | None) -> Money | None:
            if money is None:
                return None
            return Money(amount=money.amount * rate, currency=self._base_currency)

        return HistoricalPriceBar(
            symbol=bar.symbol,
            native_currency=self._base_currency,
            open_price=scale(bar.open_price),
            high_price=scale(bar.high_price),
            low_price=scale(bar.low_price),
            close_price=scale(bar.close_price),
            volume=bar.volume,
            timestamp=bar.timestamp,
            adjusted_close_price=scale(bar.adjusted_close_price),
            split_coefficient=bar.split_coefficient,
            dividend_amount=scale(bar.dividend_amount),
            source=bar.source,
        )

    async def get_quote(
        self,
        request: QuoteRequest,
    ) -> QuoteView:
        quote = await self._quote_repository.get_quote(
            request.symbol,
        )

        # Convert every price into the base currency (INR) so the user only
        # ever sees INR, regardless of the instrument's native trading currency.
        last_price = await self._to_base_money(quote.last_price)
        open_price = await self._to_base_money(quote.open_price)
        high_price = await self._to_base_money(quote.high_price)
        low_price = await self._to_base_money(quote.low_price)
        previous_close = await self._to_base_money(quote.previous_close)
        currency = last_price.currency if last_price else quote.native_currency

        return QuoteView(
            symbol=quote.symbol,
            currency=currency,
            last_price=str(last_price.amount),
            open_price=str(open_price.amount) if open_price else None,
            high_price=str(high_price.amount) if high_price else None,
            low_price=str(low_price.amount) if low_price else None,
            previous_close=str(previous_close.amount) if previous_close else None,
            volume=quote.volume,
            as_of=quote.as_of,
        )

    async def get_historical_prices(
        self,
        request: HistoricalPriceRequest,
    ) -> HistoricalPriceSeriesView:
        self._validate_history_window(request.start_at, request.end_at)
        symbol = self._normalize_symbol(request.symbol)

        if request.auto_sync and self._historical_price_provider is not None:
            await self.sync_historical_prices(
                SyncHistoricalPricesRequest(
                    symbol=symbol,
                    start_at=request.start_at,
                    end_at=request.end_at,
                )
            )

        bars = await self._historical_price_repository.get_price_history(
            symbol=symbol,
            start_at=request.start_at,
            end_at=request.end_at,
        )

        currency = bars[0].native_currency if bars else CurrencyCode("USD")

        return HistoricalPriceSeriesView(
            symbol=symbol,
            currency=currency,
            prices=tuple(
                HistoricalPricePointView(
                    timestamp=bar.timestamp,
                    open_price=str(bar.open_price.amount),
                    high_price=str(bar.high_price.amount),
                    low_price=str(bar.low_price.amount),
                    close_price=str(bar.close_price.amount),
                    adjusted_close_price=(
                        str(bar.adjusted_close_price.amount)
                        if bar.adjusted_close_price is not None
                        else None
                    ),
                    volume=bar.volume,
                    split_coefficient=(
                        str(bar.split_coefficient)
                        if bar.split_coefficient is not None
                        else None
                    ),
                    dividend_amount=(
                        str(bar.dividend_amount.amount)
                        if bar.dividend_amount is not None
                        else None
                    ),
                )
                for bar in bars
            ),
        )

    async def sync_historical_prices(
        self,
        request: SyncHistoricalPricesRequest,
    ) -> SyncHistoricalPricesView:
        self._validate_history_window(request.start_at, request.end_at)
        symbol = self._normalize_symbol(request.symbol)

        if self._historical_price_provider is None:
            return SyncHistoricalPricesView(
                symbol=symbol,
                requested_start_at=request.start_at,
                requested_end_at=request.end_at,
                fetched_count=0,
                stored_count=0,
                skipped=True,
                message="No historical price provider is configured.",
            )

        latest_timestamp = await self._historical_price_repository.get_latest_price_timestamp(
            symbol,
        )
        effective_start_at = request.start_at
        if latest_timestamp is not None and latest_timestamp >= request.start_at:
            effective_start_at = latest_timestamp + timedelta(days=1)

        if effective_start_at > request.end_at:
            return SyncHistoricalPricesView(
                symbol=symbol,
                requested_start_at=request.start_at,
                requested_end_at=request.end_at,
                fetched_count=0,
                stored_count=0,
                skipped=True,
                message="Historical prices are already current for the requested range.",
            )

        logger.info(
            "Syncing historical prices for %s from %s to %s.",
            symbol,
            effective_start_at.date(),
            request.end_at.date(),
        )

        profile = await self._load_company_profile(symbol)
        await self._persist_instrument(profile, request.asset_type)
        if self._company_profile_repository is not None:
            await self._company_profile_repository.upsert_company_profile(profile)

        bars = await self._historical_price_provider.get_price_history(
            symbol=symbol,
            start_at=effective_start_at,
            end_at=request.end_at,
        )
        # Convert to the base currency (INR) at ingestion so the warehouse
        # stores INR. A single (cached) rate is applied across the fetched
        # window; per-date historical FX is a documented future enhancement.
        converted_bars = [await self._convert_bar_to_base(bar) for bar in bars]
        stored_count = await self._historical_price_repository.upsert_price_history(
            converted_bars,
        )

        if self._commit is not None:
            await self._commit()

        logger.info(
            "Synced %s historical bars for %s.",
            stored_count,
            symbol,
        )

        return SyncHistoricalPricesView(
            symbol=symbol,
            requested_start_at=request.start_at,
            requested_end_at=request.end_at,
            fetched_count=len(bars),
            stored_count=stored_count,
        )

    async def get_company_profile(
        self,
        symbol: Symbol,
    ) -> CompanyProfileView:
        normalized_symbol = self._normalize_symbol(symbol)
        profile = None
        if self._company_profile_repository is not None:
            profile = await self._company_profile_repository.get_company_profile(
                normalized_symbol,
            )

        if profile is None:
            profile = await self._load_company_profile(normalized_symbol)
            await self._persist_instrument(profile, profile.asset_type.value)
            if self._company_profile_repository is not None:
                await self._company_profile_repository.upsert_company_profile(profile)
            if self._commit is not None:
                await self._commit()

        # Market cap is shown in the base currency (INR) for consistency; the
        # instrument's true listing currency is retained internally to know
        # what to convert from.
        market_cap_view: str | None = None
        display_currency = profile.native_currency
        if profile.market_cap is not None:
            converted = await self._to_base_money(
                Money(amount=profile.market_cap, currency=profile.native_currency)
            )
            market_cap_view = str(converted.amount) if converted else str(profile.market_cap)
            display_currency = converted.currency if converted else profile.native_currency
        elif self._fx_rate_provider is not None:
            display_currency = self._base_currency

        return CompanyProfileView(
            symbol=profile.symbol,
            instrument_name=profile.instrument_name,
            currency=display_currency,
            exchange=profile.exchange,
            asset_type=profile.asset_type.value,
            sector=profile.sector,
            industry=profile.industry,
            country=profile.country,
            website=profile.website,
            description=profile.description,
            market_cap=market_cap_view,
            employees=profile.employees,
        )

    async def search_symbols(
        self,
        request: SymbolSearchRequest,
    ) -> InstrumentSearchResultsView:
        instruments = await self._symbol_search_repository.search(
            request.query,
        )
        if self._commit is not None:
            await self._commit()

        results = tuple(
            InstrumentSearchResultView(
                symbol=instrument.symbol,
                instrument_name=instrument.instrument_name,
                exchange=instrument.exchange,
                currency=instrument.native_currency,
                asset_type=instrument.asset_type.value,
                sector=instrument.sector,
                industry=instrument.industry,
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

    async def _load_company_profile(
        self,
        symbol: Symbol,
    ) -> CompanyProfile:
        if self._company_profile_repository is not None:
            profile = await self._company_profile_repository.get_company_profile(symbol)
            if profile is not None:
                return profile

        profile = None
        if self._company_profile_provider is not None:
            profile = await self._company_profile_provider.get_company_profile(symbol)

        if profile is None:
            instrument = await self._symbol_search_repository.get_instrument(symbol)
            if instrument is not None:
                profile = CompanyProfile(
                    symbol=instrument.symbol,
                    instrument_name=instrument.instrument_name,
                    native_currency=instrument.native_currency,
                    exchange=instrument.exchange,
                    asset_type=instrument.asset_type,
                    sector=instrument.sector,
                    industry=instrument.industry,
                    country=instrument.country,
                )

        if profile is None:
            profile = CompanyProfile(
                symbol=symbol,
                instrument_name=str(symbol),
                native_currency=CurrencyCode("USD"),
                exchange="UNKNOWN",
            )

        return profile

    async def _persist_instrument(
        self,
        profile: CompanyProfile,
        requested_asset_type: str,
    ) -> None:
        asset_type = profile.asset_type
        if profile.asset_type == AssetType.STOCK and requested_asset_type:
            try:
                asset_type = AssetType(requested_asset_type)
            except ValueError:
                asset_type = profile.asset_type

        await self._symbol_search_repository.upsert_instrument(
            Instrument(
                symbol=profile.symbol,
                instrument_name=profile.instrument_name,
                exchange=profile.exchange,
                native_currency=profile.native_currency,
                asset_type=asset_type,
                sector=profile.sector,
                industry=profile.industry,
                country=profile.country,
                provider_symbol=str(profile.symbol),
            )
        )

    def _validate_history_window(
        self,
        start_at,
        end_at,
    ) -> None:
        if start_at > end_at:
            raise ValueError("Historical price start_at must be before or equal to end_at.")

    def _normalize_symbol(
        self,
        symbol: Symbol,
    ) -> Symbol:
        return Symbol(str(symbol).strip().upper())
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
