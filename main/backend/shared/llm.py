from __future__ import annotations

import json
import hashlib
import logging
import time
import uuid
from typing import Literal
from abc import ABC, abstractmethod
from typing import Any

import httpx

from backend.shared.llm_runtime import get_llm_runtime

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
        self.last_model: str | None = None
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

    async def _send(self, path: str, payload: dict[str, Any]) -> httpx.Response:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            return await client.post(
                f"{self._base_url}{path}", json=payload, headers=self._headers(),
            )

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
            response = await self._send(path, payload)
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

        return self._completion_text(data)

    def _completion_text(self, data: dict[str, Any]) -> str:
        try:
            choice = data["choices"][0]
            content = choice["message"]["content"]
            if choice.get("finish_reason") in {"length", "content_filter"}:
                raise ValueError("LLM completion was truncated or filtered.")
            if not isinstance(content, str) or not content.strip():
                raise ValueError("LLM returned no usable text.")
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("Unexpected LLM response shape.") from exc
        self.last_model = data.get("model") or self._model
        return content.strip()

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


LLMTask = Literal["extraction", "analysis", "reasoning", "strategist", "portfolio", "writer"]


class OpenRouterFreeLLM(OpenAICompatibleLLM):
    """Task-specific free routing with no paid model or embedding fallback."""

    def __init__(
        self, *, api_key: str, models: list[str], task: LLMTask,
        timeout_seconds: float = 60.0, cache_ttl_seconds: float = 300.0,
    ) -> None:
        models = list(dict.fromkeys(model.strip() for model in models))
        if not models or any(
            not (model == "openrouter/free" or model.endswith(":free"))
            for model in models
        ):
            raise ValueError("OpenRouter models must use :free or openrouter/free.")
        if not api_key.strip():
            raise ValueError("OPENROUTER_API_KEY is required for OpenRouter.")
        super().__init__(
            base_url="https://openrouter.ai/api/v1", model=models[0],
            api_key=api_key.strip(), timeout_seconds=timeout_seconds,
            connect_timeout_seconds=10.0,
        )
        self._models = models
        self._task = task
        self._deadline = timeout_seconds
        self._cache_ttl = cache_ttl_seconds

    async def _send(self, path: str, payload: dict[str, Any]) -> httpx.Response:
        return await get_llm_runtime().http.post(
            f"{self._base_url}{path}", json=payload, headers=self._headers(),
            timeout=self._timeout,
        )

    async def complete(
        self, system: str, user: str, temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> str:
        self.last_model = None
        deep = self._task in {"reasoning", "strategist", "portfolio"}
        payload: dict[str, Any] = {
            "models": self._models,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "stream": False,
            "max_tokens": max_tokens if max_tokens is not None else (
                6144 if deep else 768 if self._task == "extraction" else 2048
            ),
            "provider": {
                "allow_fallbacks": True,
                "max_price": {"prompt": 0, "completion": 0, "request": 0},
            },
            "reasoning": {"effort": "low", "exclude": True} if deep else {
                "enabled": False, "exclude": True,
            },
        }
        if self._task != "writer":
            payload["response_format"] = {"type": "json_object"}
        # Exact prompt + model/options + credential scope; no raw prompts or
        # credentials are retained as cache keys. Nonzero-temperature requests
        # intentionally remain independent.
        key = hashlib.sha256(json.dumps(
            [self._api_key, self._task, payload, self._deadline, self._cache_ttl],
            sort_keys=True,
        ).encode()).hexdigest()
        if temperature != 0:
            key = uuid.uuid4().hex

        async def generate() -> tuple[str, str]:
            return await self._generate(payload)

        try:
            content, model = await get_llm_runtime().complete(
                key, generate, ttl=self._cache_ttl if temperature == 0 else 0,
                timeout=self._deadline,
            )
        except TimeoutError as exc:
            raise LLMUnavailableError("LLM request exceeded its total time budget.") from exc
        self.last_model = model
        return content

    async def _generate(self, payload: dict[str, Any]) -> tuple[str, str]:
        started = time.monotonic()
        try:
            data = await self._post("/chat/completions", payload)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {401, 402, 403, 429, 503}:
                # Do not hammer an exhausted free quota for every article/agent.
                _mark_unavailable(self._base_url)
                try:
                    delay = float(exc.response.headers.get("Retry-After", "60"))
                    _UNAVAILABLE_UNTIL[self._base_url] = time.monotonic() + min(
                        300.0, max(60.0, delay)
                    )
                except ValueError:
                    pass
            raise
        content = self._completion_text(data)
        if self._task != "writer":
            extract_json_object(content)
        model = self.last_model or self._model
        logger.info(
            "OpenRouter task=%s model=%s duration_ms=%.0f",
            self._task, model, (time.monotonic() - started) * 1000,
        )
        return content, model

    async def embed(self, inputs: list[str], model: str) -> list[list[float]]:
        raise NotImplementedError("Free OpenRouter routing is chat-only; use local embeddings.")


def uses_openrouter(settings: Any) -> bool:
    provider = getattr(settings, "llm_provider", "auto")
    return provider == "openrouter" or (
        provider == "auto" and bool(getattr(settings, "openrouter_api_key", "").strip())
    )


def build_llm_from_settings(
    settings: Any, task: LLMTask = "reasoning",
) -> LLMClient | None:
    """Return a configured LLM client, or None when LLM use is disabled.

    Call sites use the returned client only if it is not None, so leaving
    ``LLM_ENABLED=false`` keeps every LLM-backed adapter on its deterministic,
    offline default with zero code changes.
    """

    if not getattr(settings, "llm_enabled", False):
        return None
    if uses_openrouter(settings):
        fast = settings.openrouter_fast_model
        analysis = settings.openrouter_analysis_model
        reasoning = settings.openrouter_reasoning_model
        primary = fast if task in {"extraction", "writer"} else (
            analysis if task == "analysis" else reasoning
        )
        return OpenRouterFreeLLM(
            api_key=settings.openrouter_api_key,
            models=[primary, analysis, "openrouter/free"], task=task,
            timeout_seconds=settings.openrouter_timeout_seconds,
            cache_ttl_seconds=settings.openrouter_cache_ttl_seconds,
        )
    return OpenAICompatibleLLM(
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        timeout_seconds=settings.llm_timeout_seconds,
        connect_timeout_seconds=getattr(settings, "llm_connect_timeout_seconds", 3.0),
    )


def build_llm_for_model(
    settings: Any, model: str, task: LLMTask = "reasoning",
) -> LLMClient | None:
    """Like ``build_llm_from_settings`` but pinned to a specific model.

    Used by multi-model features (e.g. the multi-agent Advisor) that run several
    different local models against the same endpoint. Returns None when LLM use
    is disabled, so callers fall back to their deterministic path.
    """

    if not getattr(settings, "llm_enabled", False):
        return None
    if uses_openrouter(settings):
        return build_llm_from_settings(settings, task=task)
    return OpenAICompatibleLLM(
        base_url=settings.llm_base_url,
        model=model,
        api_key=settings.llm_api_key,
        timeout_seconds=settings.llm_timeout_seconds,
        connect_timeout_seconds=getattr(settings, "llm_connect_timeout_seconds", 3.0),
    )


def build_embedding_llm_from_settings(settings: Any) -> LLMClient | None:
    """Keep free cloud chat separate from the existing local vector space."""
    if uses_openrouter(settings):
        return None
    return build_llm_from_settings(settings)


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
