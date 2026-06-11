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
