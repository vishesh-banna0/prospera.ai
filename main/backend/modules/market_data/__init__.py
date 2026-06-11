# Purpose:
# Marks the market data bounded context for shared market information access.
#
# Future Responsibilities:
# - Provide a single internal source of truth for quote and historical price access.
# - Prevent users, agents, and models from calling external stock APIs directly.
#
# Dependencies:
# - External market data providers through infrastructure adapters.
#
# What Should Not Live Here:
# - Simulator-specific portfolio rules.
# - HTTP bootstrapping logic.
# - Provider credentials stored inline.
