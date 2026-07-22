from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from backend.modules.market_data.domain.entities import AssetType, Instrument, MarketQuote
from backend.modules.market_data.domain.repositories import (
    QuoteRepository,
    SymbolSearchRepository,
)
from backend.modules.market_data.infrastructure.mfapi import (
    FundAwareQuoteRepository,
    MfApiDataProvider,
    MfApiQuoteRepository,
    MfApiSymbolSearchRepository,
    MultiSourceSymbolSearchRepository,
    is_mutual_fund,
    scheme_code_from_symbol,
    symbol_for_scheme,
)
from backend.shared.types import CurrencyCode, Money, Symbol


class FakeMfApiClient:
    """Stand-in for the mfapi.in HTTP client, so parsing is tested offline."""

    def __init__(self) -> None:
        self._schemes = [
            {"schemeCode": 120503, "schemeName": "Blue Chip Fund - Direct Growth"},
            {"schemeCode": 118989, "schemeName": "Flexi Cap Fund - Regular Growth"},
        ]
        self._history = {
            "120503": {
                "meta": {
                    "scheme_name": "Blue Chip Fund - Direct Growth",
                    "fund_house": "Example AMC",
                    "scheme_category": "Equity Scheme - Large Cap",
                },
                "data": [
                    {"date": "22-07-2026", "nav": "152.50"},
                    {"date": "21-07-2026", "nav": "151.00"},
                    {"date": "01-01-2020", "nav": "100.00"},
                ],
                "status": "SUCCESS",
            }
        }

    async def list_schemes(self):
        return self._schemes

    async def get_scheme(self, scheme_code: str):
        return self._history[scheme_code]

    async def get_scheme_latest(self, scheme_code: str):
        full = self._history[scheme_code]
        return {"meta": full["meta"], "data": full["data"][:1], "status": "SUCCESS"}


def test_symbol_helpers() -> None:
    assert is_mutual_fund("120503.MF") is True
    assert is_mutual_fund("120503.mf") is True
    assert is_mutual_fund("AAPL") is False
    assert is_mutual_fund("RELIANCE.NS") is False
    assert scheme_code_from_symbol("120503.MF") == "120503"
    assert symbol_for_scheme("120503") == "120503.MF"


@pytest.mark.asyncio
async def test_fund_search_returns_namespaced_instruments() -> None:
    repo = MfApiSymbolSearchRepository(FakeMfApiClient())
    results = await repo.search("blue")
    assert len(results) == 1
    assert results[0].symbol == "120503.MF"
    assert results[0].asset_type == AssetType.MUTUAL_FUND
    assert results[0].native_currency == "INR"
    assert "Blue Chip" in results[0].instrument_name


@pytest.mark.asyncio
async def test_fund_quote_is_current_nav_in_inr() -> None:
    repo = MfApiQuoteRepository(FakeMfApiClient())
    quote = await repo.get_quote(Symbol("120503.MF"))
    assert quote.native_currency == "INR"
    assert quote.last_price.amount == Decimal("152.50")


@pytest.mark.asyncio
async def test_fund_history_builds_nav_bars_in_window() -> None:
    provider = MfApiDataProvider(FakeMfApiClient())
    start = datetime(2020, 1, 1, tzinfo=UTC)
    end = datetime(2026, 7, 22, tzinfo=UTC)
    bars = await provider.get_price_history(Symbol("120503.MF"), start, end)

    assert len(bars) == 3
    # Ascending by date, priced in INR, OHLC collapsed to the NAV.
    assert bars[0].timestamp < bars[-1].timestamp
    assert bars[-1].close_price.amount == Decimal("152.50")
    assert all(bar.native_currency == "INR" for bar in bars)
    assert all(bar.open_price.amount == bar.close_price.amount for bar in bars)


@pytest.mark.asyncio
async def test_fund_history_window_excludes_out_of_range() -> None:
    provider = MfApiDataProvider(FakeMfApiClient())
    start = datetime(2026, 7, 21, tzinfo=UTC)
    end = datetime(2026, 7, 22, tzinfo=UTC)
    bars = await provider.get_price_history(Symbol("120503.MF"), start, end)
    assert len(bars) == 2  # the 2020 point is filtered out


class _StubQuoteRepo(QuoteRepository):
    def __init__(self, tag: str) -> None:
        self._tag = tag

    async def get_quote(self, symbol: Symbol) -> MarketQuote:
        return MarketQuote(
            symbol=Symbol(f"{symbol}:{self._tag}"),
            native_currency=CurrencyCode("INR"),
            last_price=Money(amount=Decimal("1"), currency=CurrencyCode("INR")),
        )


@pytest.mark.asyncio
async def test_fund_aware_quote_routes_by_suffix() -> None:
    repo = FundAwareQuoteRepository(
        equity=_StubQuoteRepo("equity"), fund=_StubQuoteRepo("fund")
    )
    equity_quote = await repo.get_quote(Symbol("AAPL"))
    fund_quote = await repo.get_quote(Symbol("120503.MF"))
    assert equity_quote.symbol.endswith(":equity")
    assert fund_quote.symbol.endswith(":fund")


class _RecordingSearchRepo(SymbolSearchRepository):
    def __init__(self) -> None:
        self.upserted: list[str] = []

    async def search(self, query: str):
        return []

    async def get_instrument(self, symbol: Symbol):
        return None

    async def upsert_instrument(self, instrument: Instrument) -> None:
        self.upserted.append(str(instrument.symbol))


@pytest.mark.asyncio
async def test_multi_source_persists_funds_to_shared_instrument_table() -> None:
    # A fund's NAV history and profile carry a foreign key to market_instruments,
    # so upserting a fund instrument must NOT be dropped (regression: FK violation).
    equity = _RecordingSearchRepo()
    merged = MultiSourceSymbolSearchRepository(
        equity=equity, fund=MfApiSymbolSearchRepository(FakeMfApiClient())
    )
    await merged.upsert_instrument(
        Instrument(
            symbol=Symbol("147946.MF"),
            instrument_name="Bandhan Small Cap Fund - Direct Growth",
            exchange="AMFI",
            native_currency=CurrencyCode("INR"),
            asset_type=AssetType.MUTUAL_FUND,
        )
    )
    assert equity.upserted == ["147946.MF"]


@pytest.mark.asyncio
async def test_multi_source_search_merges_and_dedupes() -> None:
    class _EquitySearch(MfApiSymbolSearchRepository):
        async def search(self, query: str):  # type: ignore[override]
            from backend.modules.market_data.domain.entities import Instrument

            return [
                Instrument(
                    symbol=Symbol("HDFCBANK.NS"),
                    instrument_name="HDFC Bank",
                    exchange="NSE",
                    native_currency=CurrencyCode("INR"),
                )
            ]

    merged = MultiSourceSymbolSearchRepository(
        equity=_EquitySearch(FakeMfApiClient()),
        fund=MfApiSymbolSearchRepository(FakeMfApiClient()),
    )
    results = await merged.search("f")
    symbols = [str(r.symbol) for r in results]
    # One equity plus the matching funds, no duplicates.
    assert "HDFCBANK.NS" in symbols
    assert any(s.endswith(".MF") for s in symbols)
    assert len(symbols) == len(set(symbols))
