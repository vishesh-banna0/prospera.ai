"""Verify free model availability and three synthetic completions (no DB writes).

Run from the repo root: .venv/Scripts/python.exe main/scripts/check_openrouter.py
Consumes up to three free requests. Never prints the API key or sends app data.
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.core.config import get_settings  # noqa: E402
from backend.shared.llm import (  # noqa: E402
    OpenRouterFreeLLM,
    build_llm_from_settings,
    extract_json_object,
)
from backend.shared.llm_runtime import close_llm_runtime  # noqa: E402


async def main() -> None:
    config = get_settings()
    async with httpx.AsyncClient(timeout=30) as http:
        response = await http.get("https://openrouter.ai/api/v1/models")
        response.raise_for_status()
        catalog = {m["id"]: m for m in response.json()["data"]}
    for model in {
        config.openrouter_fast_model,
        config.openrouter_analysis_model,
        config.openrouter_reasoning_model,
    }:
        entry = catalog.get(model)
        if entry is None or any(
            float(entry["pricing"].get(field, -1)) != 0
            for field in ("prompt", "completion")
        ):
            raise RuntimeError(f"Configured model is not currently listed as free: {model}")
        print(f"Verified free: {model}", flush=True)
    for task in ("extraction", "analysis", "reasoning"):
        client = build_llm_from_settings(config, task=task)
        if not isinstance(client, OpenRouterFreeLLM):
            raise RuntimeError("Enable LLMs and configure OPENROUTER_API_KEY first.")
        started = time.perf_counter()
        system = (
            'Return only a JSON object with keys "event_type" and "summary". '
            'event_type must be one of "dividend", "earnings", or "other". '
            "Use only the supplied fictional facts, and do not add market prices."
        )
        user = (
            "Synthetic example: Fictional Acme Ltd increased its quarterly dividend "
            "from 2 INR to 3 INR per share. Classify the event and summarize it."
        )
        result = await client.complete(system, user)
        cold_seconds = time.perf_counter() - started
        parsed = extract_json_object(result)
        if parsed.get("event_type") != "dividend" or not parsed.get("summary"):
            raise RuntimeError(f"Unexpected synthetic classification for {task}")
        started = time.perf_counter()
        repeated = await client.complete(system, user)
        warm_seconds = time.perf_counter() - started
        assert repeated == result
        print(
            f"PASS {task}: {client.last_model} "
            f"first={cold_seconds:.3f}s repeat={warm_seconds:.4f}s", flush=True,
        )


async def run() -> None:
    try:
        await main()
    finally:
        await close_llm_runtime()


if __name__ == "__main__":
    asyncio.run(run())
