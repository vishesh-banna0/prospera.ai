# Purpose:
# Contains market data use-case orchestration for internal consumers.
#
# Future Responsibilities:
# - Serve quotes and historical prices to simulator, agents, and future services.
# - Enforce the rule that all consumers use the market data service boundary.
#
# Dependencies:
# - backend.modules.market_data.domain
#
# What Should Not Live Here:
# - Provider SDK calls.
# - ORM storage models.
# - HTTP router declarations.
