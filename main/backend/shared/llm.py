from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class LLMUnavailableError(RuntimeError):
    """Raised when the LLM endpoint is known to be unreachable.

    Callers already fall back to their deterministic implementation on any
    exception, so raising this (instead of attempting a doomed request) simply
    makes the fallback instant during the cooldown window.
    """


# --- Process-level availability cache ------------------------------------
# The LLM is enabled by default, but in the common offline case nothing is
# listening on ``llm_base_url``. A refused TCP connection is detected almost
# instantly, but we still don't want *every* request to re-attempt it. When a
# connection-level failure happens we mark that base URL unavailable for a short
# cooldown so subsequent calls skip straight to the deterministic fallback, then
# re-probe once the cooldown lapses (so a model that comes up later is picked up).
_UNAVAILABLE_UNTIL: dict[str, float] = {}
_UNAVAILABLE_COOLDOWN_SECONDS = 60.0


def _is_marked_unavailable(base_url: str) -> bool:
    until = _UNAVAILABLE_UNTIL.get(base_url)
    return until is not None and time.monotonic() < until


def _mark_unavailable(base_url: str) -> None:
    _UNAVAILABLE_UNTIL[base_url] = time.monotonic() + _UNAVAILABLE_COOLDOWN_SECONDS


def _mark_available(base_url: str) -> None:
    _UNAVAILABLE_UNTIL.pop(base_url, None)


class LLMClient(ABC):
    """Minimal chat-completion port.

    Deliberately tiny: one ``complete`` method that takes a system + user
    prompt and returns the model's text. Keeping the surface this small means
    any backend (local Ollama, a hosted gateway, a fake for tests) can satisfy
    it, and callers never depend on a specific vendor SDK.

    ``embed`` is optional (it raises by default) so a client used only for chat
    — or a test fake implementing just ``complete`` — need not provide it.
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

    async def embed(self, inputs: list[str], model: str) -> list[list[float]]:
        raise NotImplementedError("This LLM client does not support embeddings.")


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
        connect_timeout_seconds: float = 3.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key
        # Short connect timeout so an unreachable host fails over fast; the
        # (longer) read timeout still allows slow generations to complete.
        self._timeout = httpx.Timeout(
            timeout_seconds,
            connect=min(connect_timeout_seconds, timeout_seconds),
        )

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST to the endpoint, maintaining the availability cache.

        Connection-level failures (host down, hung, or timing out on connect)
        mark the base URL unavailable for a cooldown; a successful call clears
        it. HTTP status errors (a reachable server returning 4xx/5xx) do NOT
        mark it unavailable — the server is up, this one request just failed.
        """
        if _is_marked_unavailable(self._base_url):
            raise LLMUnavailableError(f"LLM at {self._base_url} is in cooldown.")

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}{path}",
                    json=payload,
                    headers=self._headers(),
                )
                response.raise_for_status()
                data = response.json()
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.PoolTimeout) as exc:
            _mark_unavailable(self._base_url)
            raise LLMUnavailableError(f"LLM at {self._base_url} unreachable: {exc}") from exc

        _mark_available(self._base_url)
        return data

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

        data = await self._post("/chat/completions", payload)

        try:
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"Unexpected LLM response shape: {data!r}") from exc

    async def embed(self, inputs: list[str], model: str) -> list[list[float]]:
        """Return one embedding vector per input via ``/embeddings``.

        Uses the OpenAI-compatible embeddings shape (``{"model", "input"}`` ->
        ``{"data": [{"embedding": [...], "index": n}, ...]}``), which local
        Ollama and hosted gateways both implement. Results are ordered by the
        response's ``index`` so they line up with ``inputs``.
        """
        if not inputs:
            return []

        data = await self._post("/embeddings", {"model": model, "input": inputs})

        try:
            items = sorted(data["data"], key=lambda item: int(item.get("index", 0)))
            vectors = [[float(x) for x in item["embedding"]] for item in items]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ValueError(f"Unexpected embeddings response shape: {data!r}") from exc

        if len(vectors) != len(inputs):
            raise ValueError(
                f"Embeddings count mismatch: got {len(vectors)} for {len(inputs)} inputs."
            )
        return vectors


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
        connect_timeout_seconds=getattr(settings, "llm_connect_timeout_seconds", 3.0),
    )


def build_llm_for_model(settings: Any, model: str) -> LLMClient | None:
    """Like ``build_llm_from_settings`` but pinned to a specific model.

    Used by multi-model features (e.g. the multi-agent Advisor) that run several
    different local models against the same endpoint. Returns None when LLM use
    is disabled, so callers fall back to their deterministic path.
    """

    if not getattr(settings, "llm_enabled", False):
        return None
    return OpenAICompatibleLLM(
        base_url=settings.llm_base_url,
        model=model,
        api_key=settings.llm_api_key,
        timeout_seconds=settings.llm_timeout_seconds,
        connect_timeout_seconds=getattr(settings, "llm_connect_timeout_seconds", 3.0),
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
