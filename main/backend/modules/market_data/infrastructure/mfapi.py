from __future__ import annotations

import asyncio
import time as _time
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from backend.core.exceptions import MarketDataProviderError, MarketDataUnavailableError
from backend.core.logging import get_logger
from backend.modules.market_data.application.providers import (
    CompanyProfileProviderContract,
    HistoricalPriceProviderContract,
)
from backend.modules.market_data.domain.entities import (
    AssetType,
    CompanyProfile,
    HistoricalPriceBar,
    Instrument,
    MarketQuote,
)
from backend.modules.market_data.domain.repositories import (
    QuoteRepository,
    SymbolSearchRepository,
)
from backend.shared.types import CurrencyCode, Money, Symbol, Timestamp

logger = get_logger(__name__)

# Indian mutual funds have no ticker; they are identified by an AMFI scheme code.
# We namespace them with a ".MF" suffix so they slot into the existing symbol
# system the same way ".NS"/".BO" mark NSE/BSE listings. e.g. "120503.MF".
MUTUAL_FUND_SUFFIX = ".MF"

INR = CurrencyCode("INR")
_AMFI_EXCHANGE = "AMFI"
_MFAPI_BASE_URL = "https://api.mfapi.in"
_SOURCE = "mfapi.in"


def is_mutual_fund(symbol: Symbol | str) -> bool:
    """True when a symbol names an Indian mutual fund (our ``<code>.MF`` form)."""
    return str(symbol).strip().upper().endswith(MUTUAL_FUND_SUFFIX)


def scheme_code_from_symbol(symbol: Symbol | str) -> str:
    """"120503.MF" -> "120503". Assumes ``is_mutual_fund`` is already true."""
    text = str(symbol).strip()
    return text[: -len(MUTUAL_FUND_SUFFIX)] if is_mutual_fund(text) else text


def symbol_for_scheme(scheme_code: str | int) -> Symbol:
    """"120503" -> "120503.MF"."""
    return Symbol(f"{str(scheme_code).strip()}{MUTUAL_FUND_SUFFIX}")


# The full scheme list (~11k funds, ~2 MB) rarely changes, so cache it at module
# scope with a TTL. Dependencies rebuild the client per request, so an
# instance-level cache would never be reused — this global one is.
_scheme_list: list[dict[str, Any]] | None = None
_scheme_list_at: float = 0.0
_scheme_list_lock = asyncio.Lock()
_SCHEME_LIST_TTL_SECONDS = 12 * 60 * 60


class MfApiClient:
    """Minimal async client for mfapi.in — a free, key-less mirror of AMFI's
    official mutual-fund NAV data (scheme list, current NAV, and full history)."""

    def __init__(
        self,
        base_url: str = _MFAPI_BASE_URL,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._http_client = http_client

    async def list_schemes(self) -> list[dict[str, Any]]:
        """Every scheme as ``{"schemeCode": int, "schemeName": str}``. Cached."""
        global _scheme_list, _scheme_list_at
        fresh = (
            _scheme_list is not None
            and (_time.monotonic() - _scheme_list_at) < _SCHEME_LIST_TTL_SECONDS
        )
        if fresh:
            return _scheme_list  # type: ignore[return-value]

        async with _scheme_list_lock:
            # Re-check inside the lock in case another task just refreshed it.
            fresh = (
                _scheme_list is not None
                and (_time.monotonic() - _scheme_list_at) < _SCHEME_LIST_TTL_SECONDS
            )
            if fresh:
                return _scheme_list  # type: ignore[return-value]

            payload = await self._get("/mf")
            if not isinstance(payload, list):
                raise MarketDataProviderError("mfapi.in scheme list was not a list.")
            _scheme_list = [item for item in payload if isinstance(item, dict)]
            _scheme_list_at = _time.monotonic()
            return _scheme_list

    async def get_scheme(self, scheme_code: str) -> dict[str, Any]:
        """Full NAV history + metadata for one scheme (newest-first ``data``)."""
        payload = await self._get(f"/mf/{scheme_code}")
        if not isinstance(payload, dict):
            raise MarketDataProviderError("mfapi.in scheme response was not an object.")
        return payload

    async def get_scheme_latest(self, scheme_code: str) -> dict[str, Any]:
        """Latest NAV only for one scheme."""
        payload = await self._get(f"/mf/{scheme_code}/latest")
        if not isinstance(payload, dict):
            raise MarketDataProviderError("mfapi.in latest response was not an object.")
        return payload

    async def _get(self, path: str) -> Any:
        try:
            if self._http_client is not None:
                response = await self._http_client.get(path)
            else:
                async with httpx.AsyncClient(base_url=self._base_url, timeout=20.0) as client:
                    response = await client.get(path)
        except httpx.RequestError as exc:
            raise MarketDataUnavailableError(f"Unable to reach mfapi.in: {exc}") from exc

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise MarketDataProviderError(
                f"mfapi.in request failed with status {exc.response.status_code}."
            ) from exc

        try:
            return response.json()
        except ValueError as exc:
            raise MarketDataProviderError("mfapi.in returned invalid JSON.") from exc


def _parse_nav_date(raw: Any) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.strptime(str(raw), "%d-%m-%Y").replace(tzinfo=UTC)
    except (TypeError, ValueError):
        return None


def _parse_nav(raw: Any) -> Decimal | None:
    if raw in (None, ""):
        return None
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return value if value > Decimal("0") else None


class MfApiQuoteRepository(QuoteRepository):
    """Current NAV as a quote, in INR (NAV is always published in rupees)."""

    def __init__(self, client: MfApiClient | None = None) -> None:
        self._client = client or MfApiClient()

    async def get_quote(self, symbol: Symbol) -> MarketQuote:
        code = scheme_code_from_symbol(symbol)
        payload = await self._client.get_scheme_latest(code)
        data = payload.get("data") or []
        if not data:
            raise MarketDataUnavailableError(f"mfapi.in has no NAV for scheme {code}.")

        nav = _parse_nav(data[0].get("nav"))
        if nav is None:
            raise MarketDataUnavailableError(f"mfapi.in returned an unusable NAV for scheme {code}.")

        return MarketQuote(
            symbol=symbol,
            native_currency=INR,
            last_price=Money(amount=nav, currency=INR),
            as_of=_parse_nav_date(data[0].get("date")) or datetime.now(UTC),
        )


class MfApiDataProvider(HistoricalPriceProviderContract, CompanyProfileProviderContract):
    """Historical NAV series and a minimal fund profile from mfapi.in. Implements
    both provider contracts so one instance covers the fund side of history and
    profile lookups (mirrors ``YFinanceHistoricalDataProvider`` for equities)."""

    def __init__(self, client: MfApiClient | None = None) -> None:
        self._client = client or MfApiClient()

    async def get_price_history(
        self,
        symbol: Symbol,
        start_at: Timestamp,
        end_at: Timestamp,
    ) -> list[HistoricalPriceBar]:
        code = scheme_code_from_symbol(symbol)
        payload = await self._client.get_scheme(code)
        data = payload.get("data") or []
        if not data:
            raise MarketDataUnavailableError(f"mfapi.in has no NAV history for scheme {code}.")

        bars: list[HistoricalPriceBar] = []
        for point in data:
            when = _parse_nav_date(point.get("date"))
            nav = _parse_nav(point.get("nav"))
            if when is None or nav is None:
                continue
            if when < start_at or when > end_at:
                continue
            price = Money(amount=nav, currency=INR)
            # A fund only has one price per day (its NAV), so OHLC collapse to it.
            bars.append(
                HistoricalPriceBar(
                    symbol=symbol,
                    native_currency=INR,
                    open_price=price,
                    high_price=price,
                    low_price=price,
                    close_price=price,
                    volume=0,
                    timestamp=when,
                    source=_SOURCE,
                )
            )

        if not bars:
            raise MarketDataUnavailableError(
                f"mfapi.in returned no NAV history for scheme {code} in the requested window."
            )
        bars.sort(key=lambda bar: bar.timestamp)
        return bars

    async def get_company_profile(self, symbol: Symbol) -> CompanyProfile | None:
        code = scheme_code_from_symbol(symbol)
        name = await _scheme_name(self._client, code)
        meta: dict[str, Any] = {}
        if name is None:
            try:
                meta = (await self._client.get_scheme(code)).get("meta") or {}
            except (MarketDataProviderError, MarketDataUnavailableError):
                meta = {}
            name = str(meta.get("scheme_name") or symbol)

        return CompanyProfile(
            symbol=symbol,
            instrument_name=name,
            native_currency=INR,
            exchange=_AMFI_EXCHANGE,
            asset_type=AssetType.MUTUAL_FUND,
            sector=str(meta.get("scheme_category")) if meta.get("scheme_category") else None,
            industry=str(meta.get("fund_house")) if meta.get("fund_house") else None,
            country="IN",
            source=_SOURCE,
            updated_at=datetime.now(UTC),
        )


class MfApiSymbolSearchRepository(SymbolSearchRepository):
    """Search Indian mutual funds by scheme name or code."""

    def __init__(self, client: MfApiClient | None = None, limit: int = 10) -> None:
        self._client = client or MfApiClient()
        self._limit = limit

    async def search(self, query: str) -> list[Instrument]:
        needle = query.strip().lower()
        if not needle:
            return []
        try:
            schemes = await self._client.list_schemes()
        except (MarketDataProviderError, MarketDataUnavailableError) as exc:
            logger.info("mfapi.in fund search unavailable for %r: %s", query, exc)
            return []

        matches = [
            scheme
            for scheme in schemes
            if needle in str(scheme.get("schemeName", "")).lower()
            or needle in str(scheme.get("schemeCode", "")).lower()
        ]
        # Names that start with the query are the most relevant; show those first.
        matches.sort(
            key=lambda scheme: (
                not str(scheme.get("schemeName", "")).lower().startswith(needle),
                str(scheme.get("schemeName", "")),
            )
        )
        return [self._to_instrument(scheme) for scheme in matches[: self._limit]]

    async def get_instrument(self, symbol: Symbol) -> Instrument | None:
        if not is_mutual_fund(symbol):
            return None
        code = scheme_code_from_symbol(symbol)
        name = await _scheme_name(self._client, code)
        if name is None:
            return None
        return Instrument(
            symbol=symbol,
            instrument_name=name,
            exchange=_AMFI_EXCHANGE,
            native_currency=INR,
            asset_type=AssetType.MUTUAL_FUND,
            provider_symbol=code,
        )

    async def upsert_instrument(self, instrument: Instrument) -> None:
        return None

    def _to_instrument(self, scheme: dict[str, Any]) -> Instrument:
        code = str(scheme.get("schemeCode", "")).strip()
        return Instrument(
            symbol=symbol_for_scheme(code),
            instrument_name=str(scheme.get("schemeName") or code),
            exchange=_AMFI_EXCHANGE,
            native_currency=INR,
            asset_type=AssetType.MUTUAL_FUND,
            provider_symbol=code,
        )


async def _scheme_name(client: MfApiClient, scheme_code: str) -> str | None:
    """Best-effort scheme name from the cached list (no per-fund call)."""
    try:
        schemes = await client.list_schemes()
    except (MarketDataProviderError, MarketDataUnavailableError):
        return None
    for scheme in schemes:
        if str(scheme.get("schemeCode", "")).strip() == str(scheme_code).strip():
            return str(scheme.get("schemeName") or scheme_code)
    return None


# ---------------------------------------------------------------------------
# Fund-aware routing wrappers
#
# Each wrapper dispatches on the ".MF" suffix: mutual funds go to mfapi.in, and
# everything else to the existing equity adapters. Because quote, history, and
# search all route the same way, funds become first-class across Markets, the
# trade desk, SIP, and Backtest from this one place.
# ---------------------------------------------------------------------------


class FundAwareQuoteRepository(QuoteRepository):
    def __init__(self, equity: QuoteRepository, fund: QuoteRepository) -> None:
        self._equity = equity
        self._fund = fund

    async def get_quote(self, symbol: Symbol) -> MarketQuote:
        if is_mutual_fund(symbol):
            return await self._fund.get_quote(symbol)
        return await self._equity.get_quote(symbol)


class FundAwareDataProvider(HistoricalPriceProviderContract, CompanyProfileProviderContract):
    def __init__(
        self,
        equity: HistoricalPriceProviderContract | CompanyProfileProviderContract,
        fund: HistoricalPriceProviderContract | CompanyProfileProviderContract,
    ) -> None:
        self._equity = equity
        self._fund = fund

    async def get_price_history(
        self,
        symbol: Symbol,
        start_at: Timestamp,
        end_at: Timestamp,
    ) -> list[HistoricalPriceBar]:
        provider = self._fund if is_mutual_fund(symbol) else self._equity
        return await provider.get_price_history(symbol, start_at, end_at)  # type: ignore[union-attr]

    async def get_company_profile(self, symbol: Symbol) -> CompanyProfile | None:
        provider = self._fund if is_mutual_fund(symbol) else self._equity
        return await provider.get_company_profile(symbol)  # type: ignore[union-attr]


class MultiSourceSymbolSearchRepository(SymbolSearchRepository):
    """Merge equity results (local cache + Finnhub) with mutual-fund results.

    Funds ARE persisted to the shared ``market_instruments`` table — a fund's NAV
    history and profile carry foreign keys to it, so the row must exist before
    those can be stored. Shadowing is prevented one level down instead: the cached
    equity search (``SqlMarketDataRepository.search``) excludes mutual funds, so a
    stored fund can never hide live equity results. Funds always come from the
    dedicated fund source here. A fund outage never breaks equity search — the
    fund source already swallows its own errors."""

    def __init__(self, equity: SymbolSearchRepository, fund: SymbolSearchRepository) -> None:
        self._equity = equity
        self._fund = fund

    async def search(self, query: str) -> list[Instrument]:
        equity_results = await self._equity.search(query)
        fund_results = await self._fund.search(query)
        seen: set[str] = set()
        merged: list[Instrument] = []
        for instrument in [*equity_results, *fund_results]:
            key = str(instrument.symbol).upper()
            if key in seen:
                continue
            seen.add(key)
            merged.append(instrument)
        return merged

    async def get_instrument(self, symbol: Symbol) -> Instrument | None:
        if is_mutual_fund(symbol):
            return await self._fund.get_instrument(symbol)
        return await self._equity.get_instrument(symbol)

    async def upsert_instrument(self, instrument: Instrument) -> None:
        # Persist funds too — the price/profile tables reference this row.
        await self._equity.upsert_instrument(instrument)
