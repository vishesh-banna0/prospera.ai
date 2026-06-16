from functools import lru_cache # For caching the settings instance to avoid redundant loading and parsing.

import os # For accessing environment variables and file paths.

from pydantic import Field # For defining fields in the Settings class with type validation and default values.
# It handles datatype mismatches (like if a required field is age = "25" then it will convert it to 25 automatically)
# field() is used to provide additional metadata and validation rules for the fields in the Settings class,
# such as default values, aliases, and descriptions.

from pydantic_settings import BaseSettings, SettingsConfigDict
# pydantic_settings is responsible for loading configuration from environment variables, .env files, and 
# other sources.
# Pydantic Settings is a powerful library for managing application configuration using Python classes. 
# It provides features like type validation, 
# automatic parsing of environment variables, and support for .env files,
# making it an excellent choice for handling configuration in a structured and maintainable way.


class Settings(BaseSettings):
    """Centralized application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="Prospera", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    app_host: str = Field(default="127.0.0.1", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")

    database_url: str = Field(
        default=os.getenv("DATABASE_URL"),
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default=os.getenv("REDIS_URL"), alias="REDIS_URL")

    market_data_provider: str = Field(
        default=os.getenv("MARKET_DATA_PROVIDER"),
        alias="MARKET_DATA_PROVIDER",
    )
    market_data_api_key: str = Field(
        default=os.getenv("MARKET_DATA_API_KEY"),
        alias="MARKET_DATA_API_KEY",
    )
    market_data_base_url: str = Field(
        default=os.getenv("MARKET_DATA_BASE_URL"),
        alias="MARKET_DATA_BASE_URL",
    )

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    # shows more detailed logs in development and less verbose logs in production, 
    # improving debugging and performance.

    @property # creates computed values that are not stored directly in the settings but derived from existing values.
    #e.g., settings.is_development is used instead of checking settings.app_env == "development" 
    # throughout the codebase, which improves readability and maintainability.
    def is_development(self) -> bool:
        return self.app_env.lower() == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def is_testing(self) -> bool:
        return self.app_env.lower() == "test"


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance for the current process."""

    return Settings()


# Purpose:
# Central place for backend configuration definitions.
#
# Future Responsibilities:
# - Describe application settings for environment variables.
# - Separate local, development, test, and production configuration concerns.
# - Define configuration required by the market data service and simulator engine.
#
# Dependencies:
# - Environment variables.
# - Potential future settings libraries such as Pydantic Settings.
#
# Future Classes / Functions:
# - Settings
# - get_settings
# - validate_required_configuration
#
# What Should Not Live Here:
# - Secret values checked into source control.
# - Runtime API calls.
# - Business validations unrelated to configuration.
