from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from datetime import timedelta
from enum import StrEnum

from backend.shared.types import EnvironmentId, Money, Symbol, Timestamp


class SipFrequency(StrEnum):
    """How often a systematic investment plan contributes."""

    WEEKLY = "weekly"
    MONTHLY = "monthly"


class SipStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


@dataclass(slots=True)
class SipPlan:
    """A recurring, forward-looking investment into one instrument.

    The plan itself never buys anything on its own — a due installment is only
    executed when the portfolio is next read and the run date has arrived (lazy
    catch-up). ``next_run_date`` is the next date an installment comes due; there
    is deliberately no "buy immediately on create" — the first installment waits
    for the first real due date.
    """

    plan_id: str
    environment_id: EnvironmentId
    symbol: Symbol
    amount: Money  # the per-installment contribution, in the environment currency
    frequency: SipFrequency
    day_of_month: int  # anchor day for monthly runs (1–28); informational for weekly
    start_date: date
    next_run_date: date
    status: SipStatus = SipStatus.ACTIVE
    end_date: date | None = None
    symbol_name: str | None = None  # display name captured at create time (funds show a code otherwise)
    installments_run: int = 0
    installments_skipped: int = 0
    created_at: Timestamp | None = None
    updated_at: Timestamp | None = None
    last_run_at: Timestamp | None = None


def clamp_day_of_month(year: int, month: int, day: int) -> int:
    """Fit ``day`` into a given month, e.g. day 31 in February becomes 28/29."""
    last = calendar.monthrange(year, month)[1]
    return max(1, min(day, last))


def next_installment_date(current: date, frequency: SipFrequency, anchor_day: int) -> date:
    """The installment date that follows ``current`` for the given frequency.

    Monthly plans keep their anchor day of the month (clamped to month length so
    the 31st safely lands on the last day of shorter months); weekly plans step
    forward seven days.
    """
    if frequency == SipFrequency.WEEKLY:
        return current + timedelta(days=7)

    year = current.year
    month = current.month + 1
    if month > 12:
        year += 1
        month = 1
    return date(year, month, clamp_day_of_month(year, month, anchor_day))
