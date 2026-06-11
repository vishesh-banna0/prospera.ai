# Purpose:
# Defines the top-level API router composition for backend endpoints.
#
# Future Responsibilities:
# - Register route groups for environments, portfolios, and market data.
# - Keep route versioning and prefix strategy consistent.
# - Provide a single place to assemble API modules into the application.
#
# Dependencies:
# - backend.api.routes.environments
# - backend.api.routes.portfolios
# - backend.api.routes.market_data
#
# Future Classes / Functions:
# - api_router
# - register_v1_routes
#
# What Should Not Live Here:
# - Endpoint implementation details.
# - Validation rules that belong in application DTOs.
# - Any business workflow logic.
