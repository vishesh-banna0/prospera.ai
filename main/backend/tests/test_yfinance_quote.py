from __future__ import annotations

from decimal import Decimal

import pytest

from backend.modules.market_data.infrastructure.repositories import YFinanceQuoteRepository
from backend.shared.types import Symbol


class _FakeYFinanceClient:
    """Returns a fixed raw fast_info payload, so the quote adapter is tested
    without touching the network."""

    def __init__(self, raw: dict) -> None:
        self._raw = raw

    async def get_quote(self, symbol: str) -> dict:
        return self._raw


def _raw(last: str, previous_close: str) -> dict:
    return {
        "last": last,
        "previous_close": previous_close,
        "open": None,
        "high": None,
        "low": None,
        "currency": "INR",
        "volume": 0,
    }


@pytest.mark.asyncio
async def test_implausible_last_price_falls_back_to_previous_close() -> None:
    # Real 523105.BO case: yfinance reports last_price 358.15 while the stock
    # actually trades near 6.94 (its previous close and daily history agree).
    repo = YFinanceQuoteRepository(client=_FakeYFinanceClient(_raw("358.15", "6.94")))
    quote = await repo.get_quote(Symbol("523105.BO"))
    assert quote.last_price.amount == Decimal("6.94")


@pytest.mark.asyncio
async def test_normal_last_price_is_kept() -> None:
    repo = YFinanceQuoteRepository(client=_FakeYFinanceClient(_raw("7.28", "6.94")))
    quote = await repo.get_quote(Symbol("523105.BO"))
    assert quote.last_price.amount == Decimal("7.28")


@pytest.mark.asyncio
async def test_within_circuit_move_is_kept() -> None:
    # A large-but-real one-day move (up ~20%) must NOT be overridden.
    repo = YFinanceQuoteRepository(client=_FakeYFinanceClient(_raw("120.00", "100.00")))
    quote = await repo.get_quote(Symbol("SOME.NS"))
    assert quote.last_price.amount == Decimal("120.00")


@pytest.mark.asyncio
async def test_missing_previous_close_keeps_last_price() -> None:
    # With nothing to compare against, the reported last price is used as-is.
    repo = YFinanceQuoteRepository(client=_FakeYFinanceClient(_raw("358.15", "")))
    quote = await repo.get_quote(Symbol("523105.BO"))
    assert quote.last_price.amount == Decimal("358.15")
