from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from backend.core.config import get_settings
from backend.modules.simulator.application.services import SimulatorService
from backend.modules.simulator.infrastructure.repositories import (
    SqlEnvironmentRepository,
    SqlHoldingRepository,
    SqlTransactionRepository,
    SqlPortfolioSnapshotRepository,
)
from backend.modules.market_data.application.services import MarketDataService
from backend.modules.market_data.infrastructure.repositories import (
    QuoteRepository,
    HistoricalPriceRepository,
    SymbolSearchRepository,
    MarketMetadataRepository,
)

# Initialize database session factory
_engine = None
_async_session_maker = None


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide database session for request."""
    global _engine, _async_session_maker
    
    if _async_session_maker is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.app_debug,
        )
        _async_session_maker = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    
    async with _async_session_maker() as session:
        yield session


async def get_simulator_service(
    session: AsyncSession = None,
) -> SimulatorService:
    """Provide simulator application service."""
    if session is None:
        settings = get_settings()
        engine = create_async_engine(settings.database_url)
        async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with async_session_maker() as session:
            pass
    
    # Instantiate repositories
    environment_repo = SqlEnvironmentRepository(session)
    holding_repo = SqlHoldingRepository(session)
    transaction_repo = SqlTransactionRepository(session)
    snapshot_repo = SqlPortfolioSnapshotRepository(session)
    
    # TODO: Instantiate use cases from application layer
    # For now, return service stub
    return SimulatorService(
        create_environment=None,
        rename_environment=None,
        delete_environment=None,
        add_virtual_cash=None,
        withdraw_virtual_cash=None,
        buy_stock=None,
        sell_stock=None,
        get_holdings=None,
        get_transactions=None,
        get_portfolio_performance=None,
    )


async def get_market_data_service(
    session: AsyncSession = None,
) -> MarketDataService:
    """Provide market data application service."""
    # TODO: Instantiate repositories from infrastructure layer
    # For now, return service stub
    return MarketDataService(
        quote_repository=None,
        historical_price_repository=None,
        symbol_search_repository=None,
        market_metadata_repository=None,
    )


"""
Purpose:
Describe dependency wiring between API layer and application services.

Responsibilities:
- Provide simulator application services to route handlers
- Provide market data application services to route handlers
- Centralize request-scoped dependency construction
- Manage database session lifecycle

Dependencies:
- backend.modules.simulator.application.services
- backend.modules.market_data.application.services
- SQLAlchemy async engine and sessions
- backend.core.config for settings

Functions:
- get_db_session: Async generator for database sessions
- get_simulator_service: Provides SimulatorService instance
- get_market_data_service: Provides MarketDataService instance

What Should Not Live Here:
- Hard-coded database sessions
- Direct environment mutations
- Provider-specific API request logic
"""
