from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.core.config import get_settings

logger = logging.getLogger(__name__)


_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


def _module_metadata() -> list[MetaData]:
    """Collect the SQLAlchemy metadata from every bounded module's ``Base``.

    Each module owns its own ``DeclarativeBase`` (there is no single global
    metadata), so the set of tables to create is assembled explicitly here.
    Imports are local to this function to avoid import cycles and to keep the
    "which tables exist" list in one obvious place.
    """

    from backend.modules.company.infrastructure.models import Base as CompanyBase
    from backend.modules.events.infrastructure.models import Base as EventsBase
    from backend.modules.market_data.infrastructure.models import Base as MarketDataBase
    from backend.modules.news.infrastructure.models import Base as NewsBase
    from backend.modules.research.infrastructure.models import Base as ResearchBase
    from backend.modules.simulator.infrastructure.models import Base as SimulatorBase

    return [
        SimulatorBase.metadata,
        MarketDataBase.metadata,
        NewsBase.metadata,
        EventsBase.metadata,
        ResearchBase.metadata,
        CompanyBase.metadata,
    ]


def get_engine() -> AsyncEngine:
    """Return the process-wide async SQLAlchemy engine (created on first use)."""

    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.app_debug,
        )
    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Return the process-wide async session factory (created on first use)."""

    global _session_maker
    if _session_maker is None:
        _session_maker = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_maker


async def create_all_tables() -> None:
    """Create every module's tables if they do not already exist.

    This is the local/offline convenience path (SQLite, or a fresh Postgres):
    it lets ``python main.py`` boot with no manual migration step. For a real
    deployment, apply the per-module SQL files under
    ``backend/modules/<module>/infrastructure/migrations/`` in date order and
    set ``DB_AUTO_CREATE=false`` instead.
    """

    engine = get_engine()
    async with engine.begin() as conn:
        for metadata in _module_metadata():
            await conn.run_sync(metadata.create_all)
    logger.info("Database schema ensured for all modules.")


async def dispose_engine() -> None:
    """Dispose the engine on shutdown so connections are closed cleanly."""

    global _engine, _session_maker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_maker = None


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yield a request-scoped async database session."""

    async with get_session_maker()() as session:
        yield session


# Purpose:
# Centralize database engine, session factory, and schema bootstrap so every
# module and the API layer share one connection pool and one place that knows
# how to create the full schema.
#
# What Should Not Live Here:
# - Business queries (belong in module repositories).
# - ORM model definitions (belong in each module's infrastructure/models.py).
