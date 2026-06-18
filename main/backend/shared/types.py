from __future__ import annotations

from dataclasses import dataclass 
# provides a decorator and functions for automatically adding special methods to user-defined classes, 
# such as __init__(), __repr__(), and __eq__().
from datetime import datetime
# provides classes for manipulating dates and times in both simple and complex ways.
from decimal import Decimal
# provides support for fast correctly-rounded decimal floating point arithmetic.
from enum import StrEnum
# provides a way to create enumerations, which are a set of symbolic names bound to unique, constant values.
from typing import NewType
# provides support for type hints, allowing for more readable and maintainable code by specifying the 
# expected data types of variables, function parameters, and return values.


EnvironmentId = NewType("EnvironmentId", str)
TransactionId = NewType("TransactionId", str)
HoldingId = NewType("HoldingId", str)
PortfolioSnapshotId = NewType("PortfolioSnapshotId", str)

Symbol = NewType("Symbol", str)
CurrencyCode = NewType("CurrencyCode", str)
Timestamp = datetime

# NewType is used to create distinct types for identifiers and other primitives, improving type safety 
# and code clarity.

# e.g. we can accidentally pass a TransactionId where an EnvironmentId is expected if we just use str,
# but using NewType helps catch such errors at type-checking time.


class OwnerType(StrEnum):
    USER = "user"
    AI = "ai"
    RL = "rl"
    BACKTEST = "backtest"


class TransactionType(StrEnum):
    BUY = "buy"
    SELL = "sell"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"


class PortfolioCurrency(StrEnum):
    INR = "INR"


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: CurrencyCode = CurrencyCode(PortfolioCurrency.INR.value)

    def __post_init__(self) -> None:
        normalized_amount = self.amount.quantize(Decimal("0.01"))
        object.__setattr__(self, "amount", normalized_amount)

    def __add__(self, other: "Money") -> "Money":
        self._assert_same_currency(other)
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._assert_same_currency(other)
        return Money(amount=self.amount - other.amount, currency=self.currency)

    def __lt__(self, other: "Money") -> bool:
        self._assert_same_currency(other)
        return self.amount < other.amount

    def __le__(self, other: "Money") -> bool:
        self._assert_same_currency(other)
        return self.amount <= other.amount

    def __gt__(self, other: "Money") -> bool:
        self._assert_same_currency(other)
        return self.amount > other.amount

    def __ge__(self, other: "Money") -> bool:
        self._assert_same_currency(other)
        return self.amount >= other.amount

    def is_negative(self) -> bool:
        return self.amount < Decimal("0")

    def is_zero(self) -> bool:
        return self.amount == Decimal("0.00")

    def _assert_same_currency(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise ValueError("Money operations require matching currencies.")


@dataclass(frozen=True, slots=True)
class PricedSymbol:
    symbol: Symbol
    native_currency: CurrencyCode


@dataclass(frozen=True, slots=True)
class FxRate:
    from_currency: CurrencyCode
    to_currency: CurrencyCode
    rate: Decimal

    def convert(self, money: Money) -> Money:
        if money.currency != self.from_currency:
            raise ValueError("FX conversion source currency does not match money currency.")

        converted_amount = (money.amount * self.rate).quantize(Decimal("0.01"))
        return Money(amount=converted_amount, currency=self.to_currency)

# Purpose:
# Defines placeholder shared types that may be reused across modules.
#
# Future Responsibilities:
# - Describe identifiers, timestamps, money-related primitives, and ownership categories.
# - Provide a common vocabulary without forcing unrelated modules to depend on each other.
#
# Dependencies:
# - None directly.
#
# Future Classes / Types:
# - EnvironmentId
# - TransactionId
# - Symbol
# - CurrencyCode
# - Timestamp
# - OwnerType
#
# What Should Not Live Here:
# - Validation logic tied to one module.
# - Database models.
# - API-specific schema objects.
