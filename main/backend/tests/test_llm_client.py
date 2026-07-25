from __future__ import annotations

import pytest

from backend.shared import llm as llm_module
from backend.shared.llm import (
    LLMUnavailableError,
    OpenAICompatibleLLM,
    build_llm_from_settings,
)


class _Settings:
    """Minimal settings stand-in for build_llm_from_settings."""

    def __init__(self, enabled: bool) -> None:
        self.llm_enabled = enabled
        self.llm_base_url = "http://localhost:11434/v1"
        self.llm_model = "llama3.1"
        self.llm_api_key = ""
        self.llm_timeout_seconds = 30.0
        self.llm_connect_timeout_seconds = 3.0


def test_build_llm_from_settings_respects_enabled_flag() -> None:
    assert build_llm_from_settings(_Settings(enabled=False)) is None
    client = build_llm_from_settings(_Settings(enabled=True))
    assert isinstance(client, OpenAICompatibleLLM)


def test_availability_cache_roundtrip() -> None:
    base = "http://cache-test.invalid/v1"
    assert llm_module._is_marked_unavailable(base) is False
    llm_module._mark_unavailable(base)
    try:
        assert llm_module._is_marked_unavailable(base) is True
    finally:
        llm_module._mark_available(base)
    assert llm_module._is_marked_unavailable(base) is False


@pytest.mark.asyncio
async def test_complete_fast_fails_when_marked_unavailable() -> None:
    # A base URL in cooldown short-circuits before any network call, so callers
    # fall back instantly instead of re-attempting a doomed request.
    base = "http://unreachable.invalid/v1"
    client = OpenAICompatibleLLM(base_url=base, model="m")
    llm_module._mark_unavailable(base)
    try:
        with pytest.raises(LLMUnavailableError):
            await client.complete(system="s", user="u")
        with pytest.raises(LLMUnavailableError):
            await client.embed(["text"], model="embed")
    finally:
        llm_module._mark_available(base)


@pytest.mark.asyncio
async def test_embed_empty_input_returns_empty_without_network() -> None:
    client = OpenAICompatibleLLM(base_url="http://never-called.invalid/v1", model="m")
    assert await client.embed([], model="embed") == []
