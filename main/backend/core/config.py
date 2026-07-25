from functools import lru_cache  # For caching the settings instance to avoid redundant loading and parsing.

from pathlib import Path

from pydantic import Field  # For defining fields in the Settings class with type validation and default values.
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


BASE_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Centralized application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="Prospera", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    app_host: str = Field(default="127.0.0.1", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")

    # Defaults to a local SQLite file so a fresh clone runs offline with zero
    # setup. Point this at PostgreSQL (postgresql+psycopg://...) for real use.
    database_url: str = Field(
        default="sqlite+aiosqlite:///./prospera.db",
        alias="DATABASE_URL",
    )

    # When true, the app creates any missing tables on startup (convenient for
    # SQLite / local dev). In production, apply the per-module SQL migrations
    # instead and set this to false.
    db_auto_create: bool = Field(default=True, alias="DB_AUTO_CREATE")

    redis_url: str = Field(
        default="redis://localhost:6379/0",
        alias="REDIS_URL",
    )

    market_data_provider: str = Field(
        default="finnhub",
        alias="MARKET_DATA_PROVIDER",
    )

    # Empty by default so the app boots without a key; market-data and news
    # endpoints then return a clear error until a real key is configured.
    market_data_api_key: str = Field(
        default="",
        alias="MARKET_DATA_API_KEY",
    )

    market_data_api_keys: str = Field(
        default="",
        alias="MARKET_DATA_API_KEYS",
    )

    market_data_base_url: str = Field(
        default="https://finnhub.io/api/v1",
        alias="MARKET_DATA_BASE_URL",
    )

    # --- Currency / FX -------------------------------------------------------
    # Prospera presents every monetary value to the user in one base currency
    # (INR). Foreign-currency prices (e.g. AAPL in USD) are converted to INR.
    # When fx_live is true, a real-time rate is fetched from yfinance (the
    # {CUR}INR=X pair) and cached; if that fetch fails, or fx_live is false, the
    # static fallback rates below are used so the app always works offline.
    base_currency: str = Field(default="INR", alias="BASE_CURRENCY")
    fx_live: bool = Field(default=True, alias="FX_LIVE")
    fx_cache_ttl_seconds: int = Field(default=3600, alias="FX_CACHE_TTL_SECONDS")
    fx_usd_inr: float = Field(default=83.0, alias="FX_USD_INR")
    fx_eur_inr: float = Field(default=90.0, alias="FX_EUR_INR")
    fx_gbp_inr: float = Field(default=105.0, alias="FX_GBP_INR")

    # --- Hosted LLM configuration --------------------------------------------
    # Prospera never downloads model weights. The LLM-backed adapters (event
    # extraction, reasoning, and research embeddings) call a hosted,
    # OpenAI-compatible endpoint (e.g. a local Ollama, vLLM, or an OpenAI
    # gateway). This is ON by default: when a model is reachable it is used, and
    # when it is not (the common offline case — nothing listening on
    # llm_base_url), the adapters fall back to their deterministic, offline
    # implementations automatically. The fallback is fast: a refused connection
    # is detected immediately and the endpoint is then skipped for a short
    # cooldown, so a missing LLM never repeatedly stalls requests. Set
    # LLM_ENABLED=false to force the deterministic path everywhere.
    llm_enabled: bool = Field(default=True, alias="LLM_ENABLED")
    llm_base_url: str = Field(
        default="http://localhost:11434/v1",
        alias="LLM_BASE_URL",
    )
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_model: str = Field(default="llama3.1", alias="LLM_MODEL")
    # Embedding model for the research RAG store (Tier 5). Ollama exposes
    # OpenAI-compatible embeddings; "nomic-embed-text" is a common local choice.
    # When the embeddings call fails, research falls back to the deterministic
    # hashing embedder.
    llm_embedding_model: str = Field(
        default="nomic-embed-text",
        alias="LLM_EMBEDDING_MODEL",
    )
    llm_timeout_seconds: float = Field(default=30.0, alias="LLM_TIMEOUT_SECONDS")
    # Connection-establishment timeout. Kept short so a firewalled/hung endpoint
    # fails over to the offline fallback quickly (a refused connection is already
    # instant; this only bounds the "host silently drops packets" case).
    llm_connect_timeout_seconds: float = Field(
        default=3.0,
        alias="LLM_CONNECT_TIMEOUT_SECONDS",
    )

    # --- Authentication ------------------------------------------------------
    # Simple username/password auth. Passwords are stored as PBKDF2-SHA256 hashes;
    # login issues an HMAC-signed token valid for auth_token_ttl_hours. The secret
    # ships with a dev default so the app runs out of the box — set a strong
    # AUTH_SECRET_KEY in .env for anything beyond local use.
    auth_secret_key: str = Field(
        default="dev-insecure-change-me",
        alias="AUTH_SECRET_KEY",
    )
    auth_token_ttl_hours: float = Field(
        default=168.0,  # 7 days
        alias="AUTH_TOKEN_TTL_HOURS",
    )

    # --- Advisor (multi-agent) model assignments -----------------------------
    # The AI Advisor runs a small team of role-specialized agents, each on its
    # own local model (this is the multi-agent design). Any model that isn't
    # installed just makes that one agent fall back to deterministic logic, so
    # the Advisor always works. Defaults use commonly-installed Ollama models.
    advisor_analyst_model: str = Field(
        default="qwen2.5:7b",
        alias="ADVISOR_ANALYST_MODEL",
    )
    advisor_strategist_model: str = Field(
        default="llama3:8b",
        alias="ADVISOR_STRATEGIST_MODEL",
    )
    advisor_writer_model: str = Field(
        default="qwen2.5:7b",
        alias="ADVISOR_WRITER_MODEL",
    )

    # --- News auto-sync (background scheduler) -------------------------------
    # The news warehouse is pull-then-store. With auto-sync on, the backend
    # refreshes it on a timer so the UI is always current without anyone running
    # a manual sync — reads never wait on the network. Requires a market-data
    # (Finnhub) key; without one, auto-sync is skipped quietly.
    news_auto_sync_enabled: bool = Field(default=True, alias="NEWS_AUTO_SYNC_ENABLED")
    news_sync_interval_minutes: float = Field(
        default=30.0,
        alias="NEWS_SYNC_INTERVAL_MINUTES",
    )
    # Comma-separated categories to refresh. "global" also feeds india/sector via
    # classification, so it is a good default; add "company" only with symbols.
    news_sync_categories: str = Field(default="global", alias="NEWS_SYNC_CATEGORIES")
    news_sync_limit: int = Field(default=50, alias="NEWS_SYNC_LIMIT")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    # shows more detailed logs in development and less verbose logs in production,
    # improving debugging and performance.

    @property  # creates computed values that are not stored directly in the settings but derived from existing values.
    # e.g., settings.is_development is used instead of checking settings.app_env == "development"
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
