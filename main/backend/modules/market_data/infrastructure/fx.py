from __future__ import annotations

import logging
import time
from decimal import Decimal

from backend.modules.market_data.application.providers import FxRateProviderContract
from backend.modules.market_data.infrastructure.clients import YFinanceClient
from backend.shared.fx import build_rate_table

logger = logging.getLogger(__name__)


class StaticFxRateProvider(FxRateProviderContract):
    """Offline FX rates from a configurable table (base currency = INR).

    Deterministic and network-free, so it is the default in tests and the
    fallback whenever a live rate cannot be fetched. Unknown currencies resolve
    to 1 (treated as already-in-base) so a missing rate never crashes a quote.
    """

    def __init__(
        self,
        base_currency: str = "INR",
        overrides: dict[str, float] | None = None,
    ) -> None:
        self._base = base_currency.upper()
        self._rates = build_rate_table(overrides)

    async def get_rate_to_base(self, currency: str) -> Decimal:
        code = str(currency).upper()
        if code == self._base:
            return Decimal("1")
        return self._rates.get(code, Decimal("1"))


class YFinanceFxRateProvider(FxRateProviderContract):
    """Real-time FX rates via yfinance (the ``{CUR}INR=X`` pair), cached.

    Each rate is fetched at most once per ``ttl_seconds`` and memoized, so a
    bulk history conversion triggers a single lookup, not one per bar. Any
    failure (offline, bad symbol, missing price) falls back to the static
    provider, so this never breaks the app — it only improves accuracy when the
    network is available. yfinance is already a dependency, so nothing new is
    installed and no model/data is downloaded.
    """

    def __init__(
        self,
        client: YFinanceClient | None = None,
        fallback: FxRateProviderContract | None = None,
        base_currency: str = "INR",
        ttl_seconds: int = 3600,
    ) -> None:
        self._client = client or YFinanceClient()
        self._fallback = fallback or StaticFxRateProvider(base_currency=base_currency)
        self._base = base_currency.upper()
        self._ttl = ttl_seconds
        self._cache: dict[str, tuple[Decimal, float]] = {}

    async def get_rate_to_base(self, currency: str) -> Decimal:
        code = str(currency).upper()
        if code == self._base:
            return Decimal("1")

        cached = self._cache.get(code)
        if cached is not None and (time.monotonic() - cached[1]) < self._ttl:
            return cached[0]

        rate = await self._fetch_live(code)
        if rate is None:
            rate = await self._fallback.get_rate_to_base(code)
        else:
            self._cache[code] = (rate, time.monotonic())
        return rate

    async def _fetch_live(self, currency: str) -> Decimal | None:
        pair = f"{currency}{self._base}=X"
        try:
            info = await self._client.get_info(pair)
        except Exception as exc:  # network/provider issue -> fall back
            logger.warning("Live FX lookup for %s failed: %s", pair, exc)
            return None

        for key in ("regularMarketPrice", "previousClose", "bid", "ask", "open"):
            raw = info.get(key)
            if raw in (None, "", 0):
                continue
            try:
                value = Decimal(str(raw))
            except Exception:
                continue
            if value > 0:
                return value

        logger.warning("Live FX response for %s had no usable price field.", pair)
        return None


# Purpose:
# Provide the FX rate source used to present every price in INR. Static for
# offline/tests, real-time (yfinance) for accuracy, with static fallback.
#
# What Should Not Live Here:
# - Amount conversion at call sites (the service multiplies by the rate).
# - Business/trading rules.
