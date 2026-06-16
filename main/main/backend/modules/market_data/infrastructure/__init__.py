# Purpose:
# Contains concrete integrations that fulfill market data contracts.
#
# Future Responsibilities:
# - Host vendor API clients and adapter implementations.
# - Host caching integrations for quote and metadata reuse.
# - Keep provider-specific details out of the application and domain layers.
#
# Dependencies:
# - backend.modules.market_data.application.providers
# - backend.modules.market_data.domain.repositories
#
# What Should Not Live Here:
# - Simulator use-case orchestration.
# - Route handlers.
# - Core application bootstrap logic.
