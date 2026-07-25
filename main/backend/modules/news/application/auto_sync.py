from __future__ import annotations

import asyncio
import logging

from backend.core.config import Settings, get_settings
from backend.core.database import get_session_maker
from backend.modules.market_data.infrastructure.clients import FinnhubClient
from backend.modules.news.application.dto import SyncNewsRequest, SyncNewsView
from backend.modules.news.application.services import NewsIntelligenceService
from backend.modules.news.infrastructure.repositories import (
    FinnhubNewsProvider,
    SqlNewsArticleRepository,
)

logger = logging.getLogger(__name__)


def parse_categories(raw: str) -> tuple[str, ...]:
    """Split the comma-separated NEWS_SYNC_CATEGORIES setting into a clean tuple."""

    return tuple(part.strip().lower() for part in raw.split(",") if part.strip())


async def sync_news_once(settings: Settings) -> SyncNewsView | None:
    """Run one warehouse refresh in its own DB session.

    Returns None (and does nothing) when there is no market-data key, since the
    Finnhub feed can't be fetched without one — the caller then skips quietly.
    """

    if not settings.market_data_api_key.strip():
        logger.info("News auto-sync skipped: no market-data API key configured.")
        return None

    categories = parse_categories(settings.news_sync_categories) or ("global",)
    session_maker = get_session_maker()
    async with session_maker() as session:
        service = NewsIntelligenceService(
            repository=SqlNewsArticleRepository(session),
            provider=FinnhubNewsProvider(FinnhubClient(settings=settings)),
            commit=session.commit,
        )
        return await service.sync_news(
            SyncNewsRequest(
                categories=categories,
                limit=settings.news_sync_limit,
            )
        )


async def run_news_auto_sync_loop() -> None:
    """Background task: refresh the news warehouse on a fixed interval.

    Syncs once shortly after boot, then repeats every
    ``NEWS_SYNC_INTERVAL_MINUTES``. Best-effort — a failed cycle is logged and
    the loop keeps going; cancellation (on shutdown) exits cleanly.
    """

    settings = get_settings()
    interval_seconds = max(1.0, settings.news_sync_interval_minutes) * 60.0
    logger.info(
        "News auto-sync enabled: every %.0f min (categories=%s).",
        settings.news_sync_interval_minutes,
        settings.news_sync_categories,
    )
    try:
        while True:
            try:
                result = await sync_news_once(settings)
                if result is not None:
                    logger.info(
                        "News auto-sync: fetched %d, stored %d, duplicates %d.",
                        result.fetched_count,
                        result.stored_count,
                        result.duplicate_count,
                    )
            except Exception as exc:  # one bad cycle must not kill the loop
                logger.warning("News auto-sync cycle failed: %s", exc)
            await asyncio.sleep(interval_seconds)
    except asyncio.CancelledError:
        logger.info("News auto-sync loop stopped.")
        raise


# Purpose:
# Keep the news warehouse fresh without manual intervention — a small interval
# scheduler that reuses the existing NewsIntelligenceService sync path.
#
# What Should Not Live Here:
# - The sync/classification logic itself (belongs in NewsIntelligenceService).
# - HTTP route wiring (belongs in the API layer / app lifecycle).
