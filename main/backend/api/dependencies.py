# Purpose:
# Describes dependency wiring between the API layer and application services.
#
# Future Responsibilities:
# - Provide simulator application services to route handlers.
# - Provide market data application services to route handlers.
# - Centralize request-scoped dependency construction.
#
# Dependencies:
# - backend.modules.simulator.application.services
# - backend.modules.market_data.application.services
#
# Future Classes / Functions:
# - get_simulator_service
# - get_market_data_service
# - get_request_context
#
# What Should Not Live Here:
# - Hard-coded database sessions.
# - Direct environment mutations.
# - Provider-specific API request logic.
