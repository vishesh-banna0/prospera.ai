# Purpose:
# Declares persistence contracts required by the simulator domain and application layers.
#
# Future Responsibilities:
# - Define how environments are loaded and saved.
# - Define how holdings and transactions are queried per environment.
# - Preserve environment isolation as a first-class repository concern.
#
# Dependencies:
# - backend.modules.simulator.domain.entities
#
# Future Classes / Interfaces:
# - EnvironmentRepository
# - HoldingRepository
# - TransactionRepository
# - PortfolioSnapshotRepository
#
# What Should Not Live Here:
# - SQLAlchemy models.
# - Query implementations.
# - API pagination response formatting.
