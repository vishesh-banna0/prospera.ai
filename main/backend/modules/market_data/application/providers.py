# Purpose:
# Declares provider-facing contracts used by the market data service.
#
# Future Responsibilities:
# - Define the interface each external market data adapter must satisfy.
# - Allow provider changes without breaking simulator or API consumers.
# - Support future fallback strategies across multiple vendors.
#
# Dependencies:
# - backend.modules.market_data.domain.entities
#
# Future Classes / Interfaces:
# - MarketDataProvider
# - QuoteProviderContract
# - HistoricalPriceProviderContract
# - SymbolSearchProviderContract
#
# What Should Not Live Here:
# - Concrete HTTP request code.
# - API serialization.
# - Portfolio valuation logic.
