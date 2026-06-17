from __future__ import annotations

from abc import ABC
from abc import abstractmethod

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
