from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from backend.modules.market_data.application.dto import QuoteView
from backend.modules.simulator.application.commands import (
    AddVirtualCashUseCase,
    BuyStockUseCase,
    CreateEnvironmentUseCase,
    SellStockUseCase,
    WithdrawVirtualCashUseCase,
)
from backend.modules.simulator.application.dto import (
    CashAdjustmentInput,
    CreateEnvironmentInput,
    TradeOrderInput,
)
from backend.modules.simulator.application.queries import (
    GetEnvironmentUseCase,
    GetHoldingsUseCase,
    GetPortfolioPerformanceUseCase,
    GetTransactionsUseCase,
)
from backend.modules.simulator.infrastructure.models import Base
from backend.modules.simulator.infrastructure.repositories import (
    SqlEnvironmentRepository,
    SqlHoldingRepository,
    SqlTransactionRepository,
)
from backend.shared.types import Money, OwnerType, TransactionType


class StubMarketDataService:
    """Duck-typed stand-in for MarketDataService.get_quote used by simulator use cases."""

    def __init__(self, prices: dict[str, Decimal]) -> None:
        self._prices = prices

    async def get_quote(self, request) -> QuoteView:
        price = self._prices[str(request.symbol)]
        return QuoteView(
            symbol=request.symbol,
            currency="USD",
            last_price=str(price),
        )


async def _build_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    return engine, session_maker()


@pytest.mark.asyncio
async def test_create_environment_roundtrips_through_sql_repository() -> None:
    engine, session = await _build_session()
    try:
        environment_repo = SqlEnvironmentRepository(session)
        create_environment = CreateEnvironmentUseCase(environment_repo)
        get_environment = GetEnvironmentUseCase(environment_repo)

        created = await create_environment.execute(
            CreateEnvironmentInput(name="Test Portfolio", owner_type=OwnerType.USER)
        )
        await session.commit()

        fetched = await get_environment.execute(created.environment_id)

        assert fetched.environment_id == created.environment_id
        assert fetched.name == "Test Portfolio"
        assert fetched.owner_type == OwnerType.USER
        assert fetched.cash_balance == "0.00"
        assert fetched.created_at is not None
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_buy_sell_flow_updates_holdings_transactions_and_performance() -> None:
    engine, session = await _build_session()
    try:
        environment_repo = SqlEnvironmentRepository(session)
        holding_repo = SqlHoldingRepository(session)
        transaction_repo = SqlTransactionRepository(session)
        market_data_service = StubMarketDataService({"AAPL": Decimal("100")})

        create_environment = CreateEnvironmentUseCase(environment_repo)
        add_cash = AddVirtualCashUseCase(environment_repo, transaction_repo)
        buy_stock = BuyStockUseCase(
            environment_repo, holding_repo, transaction_repo, market_data_service
        )
        sell_stock = SellStockUseCase(
            environment_repo, holding_repo, transaction_repo, market_data_service
        )
        get_holdings = GetHoldingsUseCase(holding_repo, market_data_service)
        get_transactions = GetTransactionsUseCase(transaction_repo)
        get_performance = GetPortfolioPerformanceUseCase(
            environment_repo, holding_repo, market_data_service
        )

        environment = await create_environment.execute(
            CreateEnvironmentInput(name="Buy Sell Env", owner_type=OwnerType.USER)
        )
        env_id = environment.environment_id

        await add_cash.execute(
            CashAdjustmentInput(
                environment_id=env_id,
                amount=Money(amount=Decimal("10000"), currency="USD"),
            )
        )

        await buy_stock.execute(
            TradeOrderInput(
                environment_id=env_id,
                symbol="AAPL",
                quantity=10,
                order_type=TransactionType.BUY,
            )
        )
        await buy_stock.execute(
            TradeOrderInput(
                environment_id=env_id,
                symbol="AAPL",
                quantity=10,
                order_type=TransactionType.BUY,
            )
        )
        await session.commit()

        holdings = await get_holdings.execute(env_id)
        assert len(holdings) == 1
        assert holdings[0].symbol == "AAPL"
        assert holdings[0].quantity == 20.0
        assert holdings[0].average_cost == "100.00"
        assert holdings[0].market_value == "2000.00"

        await sell_stock.execute(
            TradeOrderInput(
                environment_id=env_id,
                symbol="AAPL",
                quantity=5,
                order_type=TransactionType.SELL,
            )
        )
        await session.commit()

        holdings = await get_holdings.execute(env_id)
        assert holdings[0].quantity == 15.0

        transactions = await get_transactions.execute(env_id)
        assert len(transactions) == 4  # deposit + buy + buy + sell
        assert transactions[0].transaction_type == TransactionType.SELL

        performance = await get_performance.execute(env_id)
        # cash: 10000 - 1000 - 1000 + 500 = 8500; holdings: 15 * 100 = 1500
        assert performance.cash_balance == "8500.00"
        assert performance.portfolio_value == "10000.00"
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_withdraw_more_than_balance_raises() -> None:
    engine, session = await _build_session()
    try:
        environment_repo = SqlEnvironmentRepository(session)
        transaction_repo = SqlTransactionRepository(session)
        create_environment = CreateEnvironmentUseCase(environment_repo)
        withdraw_cash = WithdrawVirtualCashUseCase(environment_repo, transaction_repo)

        environment = await create_environment.execute(
            CreateEnvironmentInput(name="Empty Env", owner_type=OwnerType.USER)
        )

        with pytest.raises(ValueError):
            await withdraw_cash.execute(
                CashAdjustmentInput(
                    environment_id=environment.environment_id,
                    amount=Money(amount=Decimal("100"), currency="USD"),
                )
            )
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_sell_without_holding_raises() -> None:
    engine, session = await _build_session()
    try:
        environment_repo = SqlEnvironmentRepository(session)
        holding_repo = SqlHoldingRepository(session)
        transaction_repo = SqlTransactionRepository(session)
        market_data_service = StubMarketDataService({"AAPL": Decimal("100")})

        create_environment = CreateEnvironmentUseCase(environment_repo)
        sell_stock = SellStockUseCase(
            environment_repo, holding_repo, transaction_repo, market_data_service
        )

        environment = await create_environment.execute(
            CreateEnvironmentInput(name="No Holdings Env", owner_type=OwnerType.USER)
        )

        with pytest.raises(ValueError):
            await sell_stock.execute(
                TradeOrderInput(
                    environment_id=environment.environment_id,
                    symbol="AAPL",
                    quantity=1,
                    order_type=TransactionType.SELL,
                )
            )
    finally:
        await session.close()
        await engine.dispose()
