from __future__ import annotations

import pytest

from backend.modules.news.application.auto_sync import parse_categories, sync_news_once


def test_parse_categories_cleans_and_lowercases() -> None:
    assert parse_categories("global, india , Company") == ("global", "india", "company")
    assert parse_categories("GLOBAL") == ("global",)
    assert parse_categories("") == ()
    assert parse_categories("  ,  ") == ()


class _NoKeySettings:
    """Duck-typed settings with no market-data key (sync_news_once returns early)."""

    market_data_api_key = ""
    news_sync_categories = "global"
    news_sync_limit = 50


@pytest.mark.asyncio
async def test_sync_news_once_skips_without_api_key() -> None:
    # No key -> nothing to fetch -> returns None without touching the DB/network.
    assert await sync_news_once(_NoKeySettings()) is None
