# This is created for defining some base exceptions that can be used across the backend 
# to standardize error handling and reporting.

class ProsperaError(Exception):
    """Base exception for all backend-specific errors."""


class ConfigurationError(ProsperaError):
    """Raised when required application configuration is missing or invalid."""


class DomainError(ProsperaError):
    """Base exception for business rule violations."""


class ValidationError(DomainError):
    """Raised when input data fails business validation."""


class ResourceNotFoundError(DomainError):
    """Raised when a requested resource cannot be found."""

    def __init__(self, resource_name: str, resource_id: str | int) -> None:
        self.resource_name = resource_name
        self.resource_id = resource_id
        super().__init__(f"{resource_name} with id '{resource_id}' was not found.")


class ConflictError(DomainError):
    """Raised when an operation conflicts with the current resource state."""


class EnvironmentNotFoundError(ResourceNotFoundError):
    """Raised when a simulator environment does not exist."""

    def __init__(self, environment_id: str | int) -> None:
        super().__init__("Environment", environment_id)


class HoldingNotFoundError(ResourceNotFoundError):
    """Raised when a holding does not exist in an environment."""

    def __init__(self, holding_id: str | int) -> None:
        super().__init__("Holding", holding_id)


class InsufficientCashError(DomainError):
    """Raised when an environment does not have enough cash for a trade or withdrawal."""


class InsufficientHoldingsError(DomainError):
    """Raised when an environment tries to sell more shares than it owns."""


class InvalidTradeError(DomainError):
    """Raised when a trade request is invalid for the current market or portfolio state."""


class ExternalServiceError(ProsperaError):
    """Base exception for failures caused by external systems."""


class MarketDataUnavailableError(ExternalServiceError):
    """Raised when the market data service cannot provide required data."""


class MarketDataProviderError(ExternalServiceError):
    """Raised when an external market data provider returns an error."""


class RepositoryError(ProsperaError):
    """Raised when persistence operations fail unexpectedly."""

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
