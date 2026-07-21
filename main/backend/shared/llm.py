from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    """Minimal chat-completion port.

    Deliberately tiny: one ``complete`` method that takes a system + user
    prompt and returns the model's text. Keeping the surface this small means
    any backend (local Ollama, a hosted gateway, a fake for tests) can satisfy
    it, and callers never depend on a specific vendor SDK.
    """

    @abstractmethod
    async def complete(
        self,
        system: str,
        user: str,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> str:
        raise NotImplementedError


class OpenAICompatibleLLM(LLMClient):
    """Calls any OpenAI-compatible ``/chat/completions`` endpoint over httpx.

    This is how Prospera reuses a locally-installed model **without downloading
    anything or adding a dependency**: Ollama exposes exactly this API at
    ``http://localhost:11434/v1`` (no API key needed), and hosted gateways use
    the same shape. Only ``httpx`` (already a dependency) is used.
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "",
        timeout_seconds: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key
        self._timeout = timeout_seconds

    async def complete(
        self,
        system: str,
        user: str,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "stream": False,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

        try:
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"Unexpected LLM response shape: {data!r}") from exc


def build_llm_from_settings(settings: Any) -> LLMClient | None:
    """Return a configured LLM client, or None when LLM use is disabled.

    Call sites use the returned client only if it is not None, so leaving
    ``LLM_ENABLED=false`` keeps every LLM-backed adapter on its deterministic,
    offline default with zero code changes.
    """

    if not getattr(settings, "llm_enabled", False):
        return None
    return OpenAICompatibleLLM(
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        timeout_seconds=settings.llm_timeout_seconds,
    )


def extract_json_object(text: str) -> dict[str, Any]:
    """Best-effort parse of a JSON object from an LLM response.

    Models often wrap JSON in prose or ```json fences. This tries a direct
    parse first, then falls back to the first balanced ``{...}`` span. Raises
    ValueError if nothing parseable is found, so callers can fall back safely.
    """

    text = text.strip()
    if text.startswith("```"):
        # Strip a ```json ... ``` fence.
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start : i + 1]
                    try:
                        parsed = json.loads(candidate)
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        break
        start = text.find("{", start + 1)

    raise ValueError("No JSON object found in LLM response.")


# Purpose:
# One tiny, vendor-neutral LLM client (OpenAI-compatible) so every AI phase
# reuses a locally-installed chat model with no extra packages or downloads.
#
# What Should Not Live Here:
# - Prompt wording for a specific phase (belongs in that phase's adapter).
# - Business rules.
