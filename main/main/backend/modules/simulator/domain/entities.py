# Purpose:
# Placeholder definitions for simulator domain entities.
#
# Future Responsibilities:
# - Represent isolated environments such as user, AI, RL, and backtesting portfolios.
# - Represent holdings owned inside one environment.
# - Represent transaction history used for auditability and performance analysis.
# - Represent portfolio snapshots if periodic valuation is introduced later.
#
# Dependencies:
# - backend.shared.types
# - backend.modules.simulator.domain.value_objects
#
# Future Classes:
# - SimulatorEnvironment
# - Holding
# - Transaction
# - PortfolioSnapshot
#
# Future Fields:
# - environment_id
# - owner_type
# - name
# - cash_balance
# - symbol
# - quantity
# - average_cost
# - transaction_type
# - executed_price
# - executed_at
#
# What Should Not Live Here:
# - ORM mappings.
# - HTTP serialization concerns.
# - External price fetching behavior.
