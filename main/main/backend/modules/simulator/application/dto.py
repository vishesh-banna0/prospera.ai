# Purpose:
# Defines application-layer request and response contracts for simulator workflows.
#
# Future Responsibilities:
# - Standardize input structures for environment, cash, and trade use cases.
# - Standardize output structures for holdings, transactions, and performance views.
# - Keep the API layer and future agent interfaces decoupled from domain internals.
#
# Dependencies:
# - backend.shared.types
#
# Future Classes:
# - CreateEnvironmentInput
# - RenameEnvironmentInput
# - CashAdjustmentInput
# - TradeOrderInput
# - HoldingView
# - TransactionView
# - PortfolioPerformanceView
#
# What Should Not Live Here:
# - Business rule execution.
# - Database mapping logic.
# - HTTP status code concerns.
