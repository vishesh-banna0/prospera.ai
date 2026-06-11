# Purpose:
# Defines shared exception categories used across the backend.
#
# Future Responsibilities:
# - Standardize business, validation, and integration error types.
# - Create clear boundaries between domain errors and transport-layer responses.
# - Support predictable error translation in the API layer.
#
# Dependencies:
# - None directly.
#
# Future Classes / Functions:
# - DomainError
# - ResourceNotFoundError
# - InsufficientCashError
# - MarketDataUnavailableError
#
# What Should Not Live Here:
# - HTTP-specific response objects.
# - Logging side effects.
# - Retry policies for external services.
