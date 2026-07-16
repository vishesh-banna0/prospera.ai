from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ShareQuantity:
    """
    Represents a quantity of shares owned or traded.

    Examples:
    - 10 shares
    - 5.5 shares (fractional investing)
    """

    value: Decimal

    def __post_init__(self) -> None:
        value = self.value if isinstance(self.value, Decimal) else Decimal(str(self.value))
        object.__setattr__(self, "value", value)

        if self.value <= Decimal("0"):
            raise ValueError(
                "Share quantity must be greater than zero."
            )


@dataclass(frozen=True, slots=True)
class PortfolioAllocation:
    """
    Represents a percentage allocation.

    Examples:
    - 25%
    - 60%
    """

    percentage: Decimal

    def __post_init__(self) -> None:
        if self.percentage < Decimal("0"):
            raise ValueError(
                "Allocation cannot be negative."
            )

        if self.percentage > Decimal("100"):
            raise ValueError(
                "Allocation cannot exceed 100 percent."
            )


@dataclass(frozen=True, slots=True)
class AverageCostBasis:
    """
    Average acquisition cost per share.
    """

    value: Decimal

    def __post_init__(self) -> None:
        value = self.value if isinstance(self.value, Decimal) else Decimal(str(self.value))
        object.__setattr__(self, "value", value)

        if self.value < Decimal("0"):
            raise ValueError(
                "Average cost basis cannot be negative."
            )

# Purpose:
# Placeholder definitions for small immutable simulator concepts.
#
# Future Responsibilities:
# - Model values such as money, symbol identifiers, quantity, and order side.
# - Protect the domain from invalid primitive combinations.
#
# Dependencies:
# - backend.shared.types
#
# Future Classes:
# - Money
# - TickerSymbol
# - ShareQuantity
# - TransactionSide
#
# What Should Not Live Here:
# - Persistence behavior.
# - Route validation logic.
# - Multi-step use-case orchestration.
