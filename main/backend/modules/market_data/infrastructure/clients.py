from __future__ import annotations

import asyncio
from abc import ABC
from abc import abstractmethod
from datetime import timedelta
from typing import Any

import httpx

from backend.core.exceptions import ConfigurationError
from backend.core.exceptions import MarketDataProviderError
from backend.core.exceptions import MarketDataUnavailableError
from backend.core.config import Settings
from backend.core.config import get_settings


class ExternalMarketApiClient(ABC):
    """
    Base class for external market data clients.

    Responsibilities:
    - Store provider configuration.
    - Store authentication details.
    - Provide common behavior shared across providers.

    Future Implementations:
    - FinnhubClient
    - PolygonClient
    - TwelveDataClient
    - AlphaVantageClient
    """

    def __init__(
        self,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()

    @property
    def provider_name(self) -> str:
        return self._settings.market_data_provider

    @property
    def api_key(self) -> str:
        return self._settings.market_data_api_key

    @property
    def api_keys(self) -> tuple[str, ...]:
        raw_keys = [
            self._settings.market_data_api_key,
            *str(getattr(self._settings, "market_data_api_keys", "")).split(","),
        ]
        keys: list[str] = []
        for raw_key in raw_keys:
            key = str(raw_key).strip()
            if not key or key == "replace_with_real_api_key" or key in keys:
                continue
            keys.append(key)
        return tuple(keys)

    @property
    def base_url(self) -> str:
        return self._settings.market_data_base_url

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Verify that the provider is reachable and credentials are valid.
        """
        raise NotImplementedError


class FinnhubClient(ExternalMarketApiClient):
    """
    Minimal Finnhub HTTP client with provider-specific error handling.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(settings=settings)
        self._http_client = http_client

    async def health_check(self) -> bool:
        try:
            response = await self._get(
                "/stock/symbol",
                {
                    "exchange": "US",
                    "mic": "XNAS",
                },
            )
        except (MarketDataProviderError, MarketDataUnavailableError):
            return False

        return isinstance(response, list)

    async def get_quote(
        self,
        symbol: str,
    ) -> dict[str, Any]:
        payload = await self._get(
            "/quote",
            {
                "symbol": symbol,
            },
        )

        if not isinstance(payload, dict):
            raise MarketDataProviderError("Finnhub quote response was not an object.")

        return payload

    async def get_company_profile(
        self,
        symbol: str,
    ) -> dict[str, Any]:
        payload = await self._get(
            "/stock/profile2",
            {
                "symbol": symbol,
            },
        )

        if not isinstance(payload, dict):
            raise MarketDataProviderError("Finnhub company profile response was not an object.")

        return payload

    async def search_symbols(
        self,
        query: str,
    ) -> list[dict[str, Any]]:
        payload = await self._get(
            "/search",
            {
                "q": query,
            },
        )

        if not isinstance(payload, dict):
            raise MarketDataProviderError("Finnhub symbol search response was not an object.")

        results = payload.get("result", [])
        if not isinstance(results, list):
            raise MarketDataProviderError("Finnhub symbol search results were not a list.")

        normalized_results: list[dict[str, Any]] = []
        for item in results:
            if isinstance(item, dict):
                normalized_results.append(item)

        return normalized_results

    async def get_market_status(
        self,
        exchange: str = "US",
    ) -> dict[str, Any]:
        payload = await self._get(
            "/stock/market-status",
            {
                "exchange": exchange,
            },
        )

        if not isinstance(payload, dict):
            raise MarketDataProviderError("Finnhub market status response was not an object.")

        return payload

    async def get_market_news(
        self,
        category: str = "general",
        min_id: int = 0,
    ) -> list[dict[str, Any]]:
        payload = await self._get(
            "/news",
            {
                "category": category,
                "minId": min_id,
            },
        )

        if not isinstance(payload, list):
            raise MarketDataProviderError("Finnhub market news response was not a list.")

        return [item for item in payload if isinstance(item, dict)]

    async def get_company_news(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        payload = await self._get(
            "/company-news",
            {
                "symbol": symbol,
                "from": start_date,
                "to": end_date,
            },
        )

        if not isinstance(payload, list):
            raise MarketDataProviderError("Finnhub company news response was not a list.")

        return [item for item in payload if isinstance(item, dict)]

    async def _get(
        self,
        path: str,
        params: dict[str, Any],
    ) -> Any:
        api_keys = self.api_keys
        if not api_keys:
            raise ConfigurationError(
                "MARKET_DATA_API_KEY or MARKET_DATA_API_KEYS must include a valid Finnhub API key."
            )

        last_provider_error: MarketDataProviderError | None = None
        for api_key in api_keys:
            try:
                return await self._get_with_key(path, params, api_key)
            except MarketDataProviderError as exc:
                if not self._is_retryable_key_error(str(exc)):
                    raise
                last_provider_error = exc

        if last_provider_error is not None:
            raise last_provider_error

        raise MarketDataProviderError("Finnhub request failed for all configured API keys.")

    async def _get_with_key(
        self,
        path: str,
        params: dict[str, Any],
        api_key: str,
    ) -> Any:
        merged_params = {**params, "token": api_key}

        try:
            if self._http_client is not None:
                response = await self._http_client.get(
                    path,
                    params=merged_params,
                )
            else:
                async with httpx.AsyncClient(
                    base_url=self.base_url.rstrip("/"),
                    timeout=10.0,
                ) as client:
                    response = await client.get(
                        path,
                        params=merged_params,
                    )
        except httpx.RequestError as exc:
            raise MarketDataUnavailableError(
                f"Unable to reach Finnhub: {exc}"
            ) from exc

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            raise MarketDataProviderError(
                f"Finnhub request failed with status {status_code}."
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise MarketDataProviderError("Finnhub returned invalid JSON.") from exc

        if isinstance(payload, dict) and payload.get("error"):
            raise MarketDataProviderError(str(payload["error"]))

        return payload

    def _is_retryable_key_error(
        self,
        message: str,
    ) -> bool:
        normalized = message.lower()
        return any(
            token in normalized
            for token in (
                "status 401",
                "status 403",
                "status 429",
                "invalid api key",
                "api limit",
                "rate limit",
                "too many requests",
            )
        )


class YFinanceClient:
    """
    Minimal yfinance wrapper for free historical market data.

    yfinance is synchronous, so this adapter runs provider calls in a worker
    thread and keeps the rest of the market data service async.
    """

    provider_name = "yfinance"

    async def get_price_history(
        self,
        symbol: str,
        start_at: Any,
        end_at: Any,
    ) -> Any:
        def load_history() -> Any:
            import yfinance as yf

            ticker = yf.Ticker(symbol)
            return ticker.history(
                start=start_at.date().isoformat(),
                end=(end_at.date() + timedelta(days=1)).isoformat(),
                interval="1d",
                auto_adjust=False,
                actions=True,
            )

        try:
            return await asyncio.to_thread(load_history)
        except Exception as exc:
            raise MarketDataUnavailableError(
                f"Unable to retrieve yfinance history for {symbol}: {exc}"
            ) from exc

    async def get_info(
        self,
        symbol: str,
    ) -> dict[str, Any]:
        def load_info() -> dict[str, Any]:
            import yfinance as yf

            raw_info = yf.Ticker(symbol).get_info()
            if not isinstance(raw_info, dict):
                return {}
            return raw_info

        try:
            return await asyncio.to_thread(load_info)
        except Exception as exc:
            raise MarketDataUnavailableError(
                f"Unable to retrieve yfinance profile for {symbol}: {exc}"
            ) from exc
# Purpose:
# Placeholder module for external market API clients and adapters.
#
# Future Responsibilities:
# - Integrate with real-time or near-real-time market data vendors.
# - Normalize vendor responses into Prospera market data entities.
# - Handle vendor authentication, rate limits, and transport retries.
#
# Dependencies:
# - backend.modules.market_data.application.providers
# - backend.modules.market_data.domain.entities
# - backend.core.config
#
# Future Classes:
# - ExternalMarketApiClient
# - VendorQuoteAdapter
# - VendorHistoricalPriceAdapter
# - VendorSymbolSearchAdapter
#
# What Should Not Live Here:
# - Simulator environment logic.
# - API endpoint declarations.
# - ORM table mappings unrelated to provider integration.
