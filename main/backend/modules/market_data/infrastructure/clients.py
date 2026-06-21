from __future__ import annotations

from abc import ABC
from abc import abstractmethod
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

    async def _get(
        self,
        path: str,
        params: dict[str, Any],
    ) -> Any:
        api_key = self.api_key.strip()
        if not api_key or api_key == "replace_with_real_api_key":
            raise ConfigurationError(
                "MARKET_DATA_API_KEY must be set to a valid Finnhub API key."
            )

        merged_params = {
            **params,
            "token": api_key,
        }

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
            raise MarketDataProviderError(
                f"Finnhub request failed with status {exc.response.status_code}."
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise MarketDataProviderError("Finnhub returned invalid JSON.") from exc

        if isinstance(payload, dict) and payload.get("error"):
            raise MarketDataProviderError(str(payload["error"]))

        return payload
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
