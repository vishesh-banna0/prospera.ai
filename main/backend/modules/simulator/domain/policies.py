from __future__ import annotations

from decimal import Decimal

from backend.modules.simulator.domain.entities import Holding
from backend.modules.simulator.domain.value_objects import ShareQuantity
from backend.shared.types import Money


def can_buy(
    available_cash: Money,
    trade_cost: Money,
) -> bool:
    """
    Determine whether an environment has enough
    cash to execute a buy order.
    """

    return available_cash >= trade_cost


def can_sell(
    holding: Holding,
    quantity_to_sell: ShareQuantity,
) -> bool:
    """
    Determine whether a holding contains enough
    shares to execute a sell order.
    """

    return holding.quantity.value >= quantity_to_sell.value


def calculate_cost_basis(
    current_quantity: ShareQuantity,
    current_average_cost: Money,
    purchased_quantity: ShareQuantity,
    purchased_price: Money,
) -> Money:
    """
    Calculate weighted average cost basis after
    purchasing additional shares.
    """

    total_current_cost = (
        current_average_cost.amount *
        current_quantity.value
    )

    total_purchase_cost = (
        purchased_price.amount *
        purchased_quantity.value
    )

    total_quantity = (
        current_quantity.value +
        purchased_quantity.value
    )

    average_cost = (
        total_current_cost +
        total_purchase_cost
    ) / total_quantity

    return Money(
        amount=average_cost,
        currency=current_average_cost.currency,
    )


def calculate_unrealized_pnl(
    quantity: ShareQuantity,
    average_cost: Money,
    current_price: Money,
) -> Money:
    """
    Calculate unrealized profit or loss.
    """

    pnl = (
        current_price.amount -
        average_cost.amount
    ) * quantity.value

    return Money(
        amount=pnl,
        currency=average_cost.currency,
    )


def calculate_market_value(
    quantity: ShareQuantity,
    current_price: Money,
) -> Money:
    """
    Current holding market value.
    """

    market_value = (
        current_price.amount *
        quantity.value
    )

    return Money(
        amount=market_value,
        currency=current_price.currency,
    )


def calculate_return_percentage(
    average_cost: Money,
    current_price: Money,
) -> Decimal:
    """
    Percentage return of a position.
    """

    if average_cost.is_zero():
        return Decimal("0")

    return (
        (
            current_price.amount -
            average_cost.amount
        )
        / average_cost.amount
    ) * Decimal("100")
# Purpose:
# Describes simulator business policies that enforce trading and cash rules.
#
# Future Responsibilities:
# - Validate whether a buy order can be funded.
# - Validate whether a sell order can be fulfilled from existing holdings.
# - Define how environment deletion should treat historical records.
# - Provide domain-level rules for valuation and performance calculations.
#
# Dependencies:
# - backend.modules.simulator.domain.entities
# - backend.modules.simulator.domain.value_objects
#
# Future Classes / Functions:
# - can_buy
# - can_sell
# - calculate_cost_basis
# - calculate_unrealized_pnl
#
# What Should Not Live Here:
# - Database transactions.
# - Route-level authorization.
# - Vendor market data integration.
