from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.modules.market_data.application.dto import QuoteView
from backend.modules.simulator.application.commands import (
    AddVirtualCashUseCase,
    CreateEnvironmentUseCase,
    DeleteEnvironmentUseCase,
)
from backend.modules.simulator.application.dto import (
    CashAdjustmentInput,
    CreateEnvironmentInput,
    CreateSipPlanInput,
)
from backend.modules.simulator.application.queries import GetHoldingsUseCase
from backend.modules.simulator.application.sip import (
    CreateSipPlanUseCase,
    ExecuteDueSipInstallmentsUseCase,
    ListSipPlansUseCase,
)
from backend.modules.simulator.domain.sip import SipFrequency
from backend.modules.simulator.infrastructure.models import Base
from backend.modules.simulator.infrastructure.repositories import (
    SqlEnvironmentRepository,
    SqlHoldingRepository,
    SqlSipPlanRepository,
    SqlTransactionRepository,
)
from backend.shared.types import Money, OwnerType


class StubMarketData:
    """get_quote returns a fixed INR price; get_historical_prices is unavailable
    so the SIP engine exercises its fallback-to-current-quote path."""

    def __init__(self, price: Decimal) -> None:
        self._price = price

    async def get_quote(self, request) -> QuoteView:
        return QuoteView(
            symbol=request.symbol,
            currency="INR",
            last_price=str(self._price),
        )

    async def get_historical_prices(self, request):
        raise RuntimeError("no history in test")


def _first_of_month_back(today: date, months: int) -> date:
    """First day of the month ``months`` before ``today`` (e.g. 3 -> three
    months ago on the 1st). Used so due dates land on a fixed, countable day."""
    month_index = (today.year * 12 + (today.month - 1)) - months
    year, month = divmod(month_index, 12)
    return date(year, month + 1, 1)


async def _build_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    return engine, session_maker()


async def _make_environment(session, cash: Decimal):
    environment_repo = SqlEnvironmentRepository(session)
    transaction_repo = SqlTransactionRepository(session)
    created = await CreateEnvironmentUseCase(environment_repo).execute(
        CreateEnvironmentInput(name="SIP Env", owner_type=OwnerType.USER)
    )
    await AddVirtualCashUseCase(environment_repo, transaction_repo).execute(
        CashAdjustmentInput(
            environment_id=created.environment_id,
            amount=Money(amount=cash, currency="INR"),
        )
    )
    return created.environment_id


@pytest.mark.asyncio
async def test_creating_a_sip_does_not_invest_immediately() -> None:
    engine, session = await _build_session()
    try:
        env_id = await _make_environment(session, Decimal("100000"))
        sip_repo = SqlSipPlanRepository(session)
        environment_repo = SqlEnvironmentRepository(session)
        holding_repo = SqlHoldingRepository(session)
        market = StubMarketData(Decimal("100"))

        start = _first_of_month_back(datetime.now(UTC).date(), 0)  # this month's 1st
        view = await CreateSipPlanUseCase(sip_repo, environment_repo, market).execute(
            CreateSipPlanInput(
                environment_id=env_id,
                symbol="AAPL",
                amount=Money(amount=Decimal("1000"), currency="INR"),
                frequency=SipFrequency.MONTHLY,
                start_date=start,
            )
        )
        await session.commit()

        assert view.next_run_date == start
        assert view.installments_run == 0
        # No holding exists yet — creation must not buy anything.
        holdings = await GetHoldingsUseCase(holding_repo, market).execute(env_id)
        assert holdings == []
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_lazy_catchup_executes_every_due_installment() -> None:
    engine, session = await _build_session()
    try:
        env_id = await _make_environment(session, Decimal("100000"))
        sip_repo = SqlSipPlanRepository(session)
        environment_repo = SqlEnvironmentRepository(session)
        holding_repo = SqlHoldingRepository(session)
        transaction_repo = SqlTransactionRepository(session)
        market = StubMarketData(Decimal("100"))

        # Start on the 1st three months ago -> due on the 1st of m-3, m-2, m-1, m.
        start = _first_of_month_back(datetime.now(UTC).date(), 3)
        await CreateSipPlanUseCase(sip_repo, environment_repo, market).execute(
            CreateSipPlanInput(
                environment_id=env_id,
                symbol="AAPL",
                amount=Money(amount=Decimal("1000"), currency="INR"),
                frequency=SipFrequency.MONTHLY,
                start_date=start,
            )
        )
        await session.commit()

        engine_use_case = ExecuteDueSipInstallmentsUseCase(
            sip_repo, environment_repo, holding_repo, transaction_repo, market
        )
        executed = await engine_use_case.execute(env_id)
        await session.commit()

        assert executed == 4  # four monthly first-of-month dates through today

        plans = await ListSipPlansUseCase(sip_repo).execute(env_id)
        assert plans[0].installments_run == 4
        assert plans[0].installments_skipped == 0
        assert plans[0].next_run_date > datetime.now(UTC).date()

        holdings = await GetHoldingsUseCase(holding_repo, market).execute(env_id)
        assert holdings[0].symbol == "AAPL"
        assert holdings[0].quantity == 40.0  # 4 * (1000 / 100)

        environment = await environment_repo.get(env_id)
        assert environment.cash_balance.amount == Decimal("96000.00")  # 100000 - 4*1000

        # Running again finds nothing due — the catch-up is idempotent.
        assert await engine_use_case.execute(env_id) == 0
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_installments_are_skipped_when_cash_runs_out() -> None:
    engine, session = await _build_session()
    try:
        env_id = await _make_environment(session, Decimal("2500"))
        sip_repo = SqlSipPlanRepository(session)
        environment_repo = SqlEnvironmentRepository(session)
        holding_repo = SqlHoldingRepository(session)
        transaction_repo = SqlTransactionRepository(session)
        market = StubMarketData(Decimal("100"))

        start = _first_of_month_back(datetime.now(UTC).date(), 3)  # 4 due installments
        await CreateSipPlanUseCase(sip_repo, environment_repo, market).execute(
            CreateSipPlanInput(
                environment_id=env_id,
                symbol="AAPL",
                amount=Money(amount=Decimal("1000"), currency="INR"),
                frequency=SipFrequency.MONTHLY,
                start_date=start,
            )
        )
        await session.commit()

        await ExecuteDueSipInstallmentsUseCase(
            sip_repo, environment_repo, holding_repo, transaction_repo, market
        ).execute(env_id)
        await session.commit()

        plans = await ListSipPlansUseCase(sip_repo).execute(env_id)
        # Only two installments fit in 2500; the rest are skipped, plan stays active.
        assert plans[0].installments_run == 2
        assert plans[0].installments_skipped == 2
        assert plans[0].status == "active"

        environment = await environment_repo.get(env_id)
        assert environment.cash_balance.amount == Decimal("500.00")
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_deleting_environment_removes_its_sip_plans() -> None:
    engine, session = await _build_session()
    try:
        env_id = await _make_environment(session, Decimal("100000"))
        sip_repo = SqlSipPlanRepository(session)
        environment_repo = SqlEnvironmentRepository(session)
        market = StubMarketData(Decimal("100"))

        start = _first_of_month_back(datetime.now(UTC).date(), 0)
        await CreateSipPlanUseCase(sip_repo, environment_repo, market).execute(
            CreateSipPlanInput(
                environment_id=env_id,
                symbol="AAPL",
                amount=Money(amount=Decimal("1000"), currency="INR"),
                frequency=SipFrequency.MONTHLY,
                start_date=start,
            )
        )
        await session.commit()
        assert len(await ListSipPlansUseCase(sip_repo).execute(env_id)) == 1

        # Deleting the portfolio must take its SIP plans with it (else the FK from
        # sip_plans -> environments blocks the delete).
        await DeleteEnvironmentUseCase(environment_repo).execute(env_id)
        await session.commit()

        assert await ListSipPlansUseCase(sip_repo).execute(env_id) == []
    finally:
        await session.close()
        await engine.dispose()
