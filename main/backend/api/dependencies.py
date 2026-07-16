from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.core.exceptions import ConfigurationError
from backend.core.config import get_settings

from backend.modules.simulator.application.services import SimulatorService

from backend.modules.simulator.application.commands import (
    CreateEnvironmentUseCase,
    RenameEnvironmentUseCase,
    DeleteEnvironmentUseCase,
    AddVirtualCashUseCase,
    WithdrawVirtualCashUseCase,
    BuyStockUseCase,
    SellStockUseCase,
)

from backend.modules.simulator.application.queries import (
    GetEnvironmentUseCase,
    GetHoldingsUseCase,
    GetTransactionsUseCase,
    GetPortfolioPerformanceUseCase,
)

from backend.modules.simulator.infrastructure.repositories import (
    SqlEnvironmentRepository,
    SqlHoldingRepository,
    SqlTransactionRepository,
    SqlPortfolioSnapshotRepository,
)

from backend.modules.market_data.application.services import MarketDataService
from backend.modules.market_data.infrastructure.clients import FinnhubClient
from backend.modules.market_data.infrastructure.repositories import (
    CompositeSymbolSearchRepository,
    FinnhubMarketMetadataRepository,
    FinnhubQuoteRepository,
    FinnhubSymbolSearchRepository,
    SqlMarketDataRepository,
    YFinanceHistoricalDataProvider,
)
from backend.modules.news.application.services import NewsIntelligenceService
from backend.modules.news.infrastructure.repositories import FinnhubNewsProvider
from backend.modules.news.infrastructure.repositories import SqlNewsArticleRepository


_engine = None
_async_session_maker = None


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide request-scoped database session.
    """
    global _engine
    global _async_session_maker

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


async def get_market_data_service(
    session: AsyncSession = Depends(get_db_session),
) -> MarketDataService:
    """
    Provide market data service.
    """
    settings = get_settings()

    provider_name = settings.market_data_provider.strip().lower()
    if provider_name != "finnhub":
        raise ConfigurationError(
            "MARKET_DATA_PROVIDER must be set to 'finnhub' for the current backend integration."
        )

    client = FinnhubClient(settings=settings)
    market_data_repository = SqlMarketDataRepository(session)
    yfinance_provider = YFinanceHistoricalDataProvider()

    return MarketDataService(
        quote_repository=FinnhubQuoteRepository(client),
        historical_price_repository=market_data_repository,
        symbol_search_repository=CompositeSymbolSearchRepository(
            storage_repository=market_data_repository,
            provider_repository=FinnhubSymbolSearchRepository(client),
        ),
        market_metadata_repository=FinnhubMarketMetadataRepository(client),
        historical_price_provider=yfinance_provider,
        company_profile_repository=market_data_repository,
        company_profile_provider=yfinance_provider,
        commit=session.commit,
    )


async def get_news_intelligence_service(
    session: AsyncSession = Depends(get_db_session),
) -> NewsIntelligenceService:
    """
    Provide news intelligence service.
    """
    settings = get_settings()

    provider_name = settings.market_data_provider.strip().lower()
    if provider_name != "finnhub":
        raise ConfigurationError(
            "MARKET_DATA_PROVIDER must be set to 'finnhub' for the current news integration."
        )

    client = FinnhubClient(settings=settings)
    return NewsIntelligenceService(
        repository=SqlNewsArticleRepository(session),
        provider=FinnhubNewsProvider(client),
        commit=session.commit,
    )


async def get_simulator_service(
    session: AsyncSession = Depends(get_db_session),
) -> SimulatorService:
    """
    Provide simulator service.
    """

    environment_repo = SqlEnvironmentRepository(session)
    holding_repo = SqlHoldingRepository(session)
    transaction_repo = SqlTransactionRepository(session)
    snapshot_repo = SqlPortfolioSnapshotRepository(session)

    market_data_service = await get_market_data_service(session)

    create_environment = CreateEnvironmentUseCase(
        environment_repository=environment_repo,
    )

    rename_environment = RenameEnvironmentUseCase(
        environment_repository=environment_repo,
    )

    delete_environment = DeleteEnvironmentUseCase(
        environment_repository=environment_repo,
    )

    add_virtual_cash = AddVirtualCashUseCase(
        environment_repository=environment_repo,
        transaction_repository=transaction_repo,
    )

    withdraw_virtual_cash = WithdrawVirtualCashUseCase(
        environment_repository=environment_repo,
        transaction_repository=transaction_repo,
    )

    buy_stock = BuyStockUseCase(
        environment_repository=environment_repo,
        holding_repository=holding_repo,
        transaction_repository=transaction_repo,
        market_data_service=market_data_service,
    )

    sell_stock = SellStockUseCase(
        environment_repository=environment_repo,
        holding_repository=holding_repo,
        transaction_repository=transaction_repo,
        market_data_service=market_data_service,
    )

    get_environment = GetEnvironmentUseCase(
        environment_repository=environment_repo,
    )

    get_holdings = GetHoldingsUseCase(
        holding_repository=holding_repo,
        market_data_service=market_data_service,
    )

    get_transactions = GetTransactionsUseCase(
        transaction_repository=transaction_repo,
    )

    get_portfolio_performance = GetPortfolioPerformanceUseCase(
        environment_repository=environment_repo,
        holding_repository=holding_repo,
        market_data_service=market_data_service,
    )

    return SimulatorService(
        create_environment=create_environment,
        rename_environment=rename_environment,
        delete_environment=delete_environment,
        add_virtual_cash=add_virtual_cash,
        withdraw_virtual_cash=withdraw_virtual_cash,
        buy_stock=buy_stock,
        sell_stock=sell_stock,
        get_environment=get_environment,
        get_holdings=get_holdings,
        get_transactions=get_transactions,
        get_portfolio_performance=get_portfolio_performance,
        commit=session.commit,
    )
