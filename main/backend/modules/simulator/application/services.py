# Purpose:
# Defines higher-level simulator application services that group related use cases.
#
# Future Responsibilities:
# - Offer a cohesive interface for the API layer and future agent clients.
# - Coordinate commands and queries under a stable simulator service boundary.
# - Support future non-HTTP consumers such as internal jobs, AI agents, and RL runners.
#
# Dependencies:
# - backend.modules.simulator.application.commands
# - backend.modules.simulator.application.queries
#
# Future Classes:
# - SimulatorService
# - EnvironmentLifecycleService
# - PortfolioService
#
# What Should Not Live Here:
# - Domain entity definitions.
# - Provider SDK logic.
# - Persistence schema details.
