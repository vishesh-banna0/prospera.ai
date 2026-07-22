from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from backend.modules.market_data.application.dto import (
    HistoricalPriceRequest,
    QuoteRequest,
)
from backend.modules.simulator.application.dto import (
    CreateSipPlanInput,
    SipPlanView,
)
from backend.modules.simulator.domain.entities import Holding, Transaction
from backend.modules.simulator.domain.policies import calculate_cost_basis, can_buy
from backend.modules.simulator.domain.repositories import (
    EnvironmentRepository,
    HoldingRepository,
    SipPlanRepository,
    TransactionRepository,
)
from backend.modules.simulator.domain.sip import (
    SipPlan,
    SipStatus,
    clamp_day_of_month,
    next_installment_date,
)
from backend.modules.simulator.domain.value_objects import ShareQuantity
from backend.shared.types import (
    CurrencyCode,
    EnvironmentId,
    Money,
    Symbol,
    TransactionType,
)

# A hard ceiling on installments executed in one catch-up pass, so a plan with a
# far-past start date can never spin forever (or hammer the price provider).
_MAX_CATCHUP_INSTALLMENTS = 600


def _to_view(plan: SipPlan) -> SipPlanView:
    return SipPlanView(
        plan_id=plan.plan_id,
        environment_id=plan.environment_id,
        symbol=plan.symbol,
        symbol_name=plan.symbol_name,
        amount=str(plan.amount.amount),
        frequency=plan.frequency.value,
        day_of_month=plan.day_of_month,
        start_date=plan.start_date,
        next_run_date=plan.next_run_date,
        end_date=plan.end_date,
        status=plan.status.value,
        installments_run=plan.installments_run,
        installments_skipped=plan.installments_skipped,
        last_run_at=plan.last_run_at,
        created_at=plan.created_at,
    )


class CreateSipPlanUseCase:
    """Create a recurring investment plan. Does NOT invest anything now — the
    first installment waits for the plan's first real due date (``start_date``)."""

    def __init__(
        self,
        sip_plan_repository: SipPlanRepository,
        environment_repository: EnvironmentRepository,
        market_data_service,
    ) -> None:
        self._sip_plan_repository = sip_plan_repository
        self._environment_repository = environment_repository
        self._market_data_service = market_data_service

    async def execute(self, request: CreateSipPlanInput) -> SipPlanView:
        environment = await self._environment_repository.get(request.environment_id)
        if environment is None:
            raise ValueError(f"Environment {request.environment_id} not found")

        if request.amount.amount <= Decimal("0"):
            raise ValueError("SIP amount must be greater than zero.")
        if request.amount.currency != environment.cash_balance.currency:
            raise ValueError(
                f"SIP currency {request.amount.currency} does not match "
                f"environment currency {environment.cash_balance.currency}."
            )

        symbol = Symbol(str(request.symbol).strip().upper())
        # Confirm the instrument is real and priceable before committing to a plan,
        # so a typo fails at create time rather than silently every month.
        try:
            await self._market_data_service.get_quote(QuoteRequest(symbol=symbol))
        except Exception as exc:  # noqa: BLE001 - surface any pricing failure as a clear error
            raise ValueError(f"Could not price {symbol}: {exc}") from exc

        start = request.start_date or datetime.now(UTC).date()
        if request.end_date is not None and request.end_date < start:
            raise ValueError("SIP end date must be on or after the start date.")

        now = datetime.now(UTC)
        plan = SipPlan(
            plan_id=str(uuid.uuid4()),
            environment_id=request.environment_id,
            symbol=symbol,
            amount=request.amount,
            frequency=request.frequency,
            day_of_month=clamp_day_of_month(start.year, start.month, start.day),
            start_date=start,
            next_run_date=start,
            status=SipStatus.ACTIVE,
            end_date=request.end_date,
            symbol_name=request.name,
            created_at=now,
            updated_at=now,
        )
        await self._sip_plan_repository.save(plan)
        return _to_view(plan)


class ListSipPlansUseCase:
    """List every SIP plan in an environment."""

    def __init__(self, sip_plan_repository: SipPlanRepository) -> None:
        self._sip_plan_repository = sip_plan_repository

    async def execute(self, environment_id: EnvironmentId) -> list[SipPlanView]:
        plans = await self._sip_plan_repository.list_by_environment(environment_id)
        return [_to_view(plan) for plan in plans]


class CancelSipPlanUseCase:
    """Cancel a plan. Installments already executed stay in the transaction
    history; only the recurring plan itself is removed."""

    def __init__(self, sip_plan_repository: SipPlanRepository) -> None:
        self._sip_plan_repository = sip_plan_repository

    async def execute(self, environment_id: EnvironmentId, plan_id: str) -> None:
        plan = await self._sip_plan_repository.get(plan_id)
        if plan is None or plan.environment_id != environment_id:
            raise ValueError(f"SIP plan {plan_id} not found")
        await self._sip_plan_repository.delete(plan_id)


class ExecuteDueSipInstallmentsUseCase:
    """The lazy catch-up engine.

    For every active plan in an environment, execute each installment whose run
    date has already arrived — pricing it at that date's real close/NAV — and
    advance the plan to its next date. Runs on a portfolio read, so no background
    scheduler is needed. Installments with insufficient cash are skipped (the
    plan keeps running); a symbol that can't be priced right now is retried on a
    later read.
    """

    def __init__(
        self,
        sip_plan_repository: SipPlanRepository,
        environment_repository: EnvironmentRepository,
        holding_repository: HoldingRepository,
        transaction_repository: TransactionRepository,
        market_data_service,
    ) -> None:
        self._sip_plan_repository = sip_plan_repository
        self._environment_repository = environment_repository
        self._holding_repository = holding_repository
        self._transaction_repository = transaction_repository
        self._market_data_service = market_data_service

    async def execute(self, environment_id: EnvironmentId) -> int:
        environment = await self._environment_repository.get(environment_id)
        if environment is None:
            return 0

        plans = await self._sip_plan_repository.list_by_environment(environment_id)
        today = datetime.now(UTC).date()
        executed = 0
        environment_dirty = False

        for plan in plans:
            if plan.status != SipStatus.ACTIVE:
                continue

            plan_changed = False
            guard = 0
            while (
                plan.status == SipStatus.ACTIVE
                and plan.next_run_date <= today
                and (plan.end_date is None or plan.next_run_date <= plan.end_date)
                and guard < _MAX_CATCHUP_INSTALLMENTS
            ):
                guard += 1
                due = plan.next_run_date

                price = await self._price_on(plan.symbol, due)
                if price is None:
                    # Can't price this installment yet (e.g. history not synced);
                    # leave the run date untouched and try again on a later read.
                    break

                if can_buy(environment.cash_balance, plan.amount) and price.amount > 0:
                    units = ShareQuantity(value=plan.amount.amount / price.amount)
                    await self._apply_installment(
                        environment, plan.symbol, units, price, plan.amount, due
                    )
                    plan.installments_run += 1
                    environment_dirty = True
                    executed += 1
                else:
                    plan.installments_skipped += 1

                plan.next_run_date = next_installment_date(
                    due, plan.frequency, plan.day_of_month
                )
                plan.last_run_at = datetime.now(UTC)
                plan.updated_at = datetime.now(UTC)
                if plan.end_date is not None and plan.next_run_date > plan.end_date:
                    plan.status = SipStatus.COMPLETED
                plan_changed = True

            if plan_changed:
                await self._sip_plan_repository.save(plan)

        if environment_dirty:
            environment.updated_at = datetime.now(UTC)
            await self._environment_repository.save(environment)

        return executed

    async def _apply_installment(
        self,
        environment,
        symbol: Symbol,
        units: ShareQuantity,
        price: Money,
        contribution: Money,
        due: date,
    ) -> None:
        # A SIP invests a fixed rupee amount, so cash falls by exactly the
        # contribution and the position grows by amount / price units.
        environment.cash_balance = Money(
            amount=environment.cash_balance.amount - contribution.amount,
            currency=environment.cash_balance.currency,
        )

        holdings = await self._holding_repository.list_by_environment(
            environment.environment_id
        )
        holding = next((h for h in holdings if h.symbol == symbol), None)

        now = datetime.now(UTC)
        if holding is None:
            holding = Holding(
                holding_id=str(uuid.uuid4()),
                environment_id=environment.environment_id,
                symbol=symbol,
                quantity=units,
                average_cost=price,
                created_at=now,
            )
        else:
            holding.average_cost = calculate_cost_basis(
                holding.quantity,
                holding.average_cost,
                units,
                price,
            )
            holding.quantity = ShareQuantity(value=holding.quantity.value + units.value)
            holding.updated_at = now
        await self._holding_repository.save(holding)

        transaction = Transaction(
            transaction_id=str(uuid.uuid4()),
            environment_id=environment.environment_id,
            transaction_type=TransactionType.BUY,
            amount=contribution,
            symbol=symbol,
            quantity=units,
            executed_price=price,
            executed_at=datetime.combine(due, time.min, tzinfo=UTC),
            notes="SIP",
        )
        await self._transaction_repository.save(transaction)

    async def _price_on(self, symbol: Symbol, due: date) -> Money | None:
        """The instrument's price as of ``due``: the last close/NAV on or before
        that date, falling back to the current quote if history isn't available."""
        start = datetime.combine(due - timedelta(days=10), time.min, tzinfo=UTC)
        end = datetime.combine(due + timedelta(days=1), time.min, tzinfo=UTC)

        try:
            series = await self._market_data_service.get_historical_prices(
                HistoricalPriceRequest(
                    symbol=symbol, start_at=start, end_at=end, auto_sync=True
                )
            )
            on_or_before = [p for p in series.prices if p.timestamp.date() <= due]
            if on_or_before:
                latest = max(on_or_before, key=lambda p: p.timestamp)
                amount = Decimal(str(latest.close_price))
                if amount > 0:
                    return Money(amount=amount, currency=CurrencyCode(str(series.currency)))
        except Exception:  # noqa: BLE001 - fall through to the live quote
            pass

        try:
            quote = await self._market_data_service.get_quote(QuoteRequest(symbol=symbol))
            amount = Decimal(str(quote.last_price))
            if amount > 0:
                return Money(amount=amount, currency=CurrencyCode(str(quote.currency)))
        except Exception:  # noqa: BLE001 - no price available for this installment yet
            pass

        return None
