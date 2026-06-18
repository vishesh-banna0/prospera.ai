from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

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

    return MarketDataService(
        quote_repository=None,
        historical_price_repository=None,
        symbol_search_repository=None,
        market_metadata_repository=None,
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

    get_holdings = GetHoldingsUseCase(
        holding_repository=holding_repo,
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
        get_holdings=get_holdings,
        get_transactions=get_transactions,
        get_portfolio_performance=get_portfolio_performance,
    )