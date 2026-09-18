from __future__ import annotations

import json
import asyncio

import httpx
import pytest
import pytest_asyncio

from backend.core.config import Settings
from backend.shared import llm as module
from backend.shared.llm_runtime import close_llm_runtime
from backend.shared.llm import (
    LLMUnavailableError,
    OpenAICompatibleLLM,
    OpenRouterFreeLLM,
    build_embedding_llm_from_settings,
    build_llm_for_model,
    build_llm_from_settings,
)


def settings(**overrides) -> Settings:
    values = {"OPENROUTER_API_KEY": "test-key", "LLM_ENABLED": True, "LLM_PROVIDER": "auto"}
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.fixture(autouse=True)
def clear_cooldown():
    module._UNAVAILABLE_UNTIL.clear()
    yield
    module._UNAVAILABLE_UNTIL.clear()


@pytest_asyncio.fixture(autouse=True)
async def close_runtime():
    yield
    await close_llm_runtime()


def mock_http(monkeypatch, handler):
    original = httpx.AsyncClient
    monkeypatch.setattr(
        module.httpx, "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )


@pytest.mark.parametrize("task,field", [
    ("extraction", "openrouter_fast_model"),
    ("writer", "openrouter_fast_model"),
    ("analysis", "openrouter_analysis_model"),
    ("reasoning", "openrouter_reasoning_model"),
    ("strategist", "openrouter_reasoning_model"),
    ("portfolio", "openrouter_reasoning_model"),
])
def test_task_routing_ignores_legacy_local_models(task, field):
    config = settings(LLM_MODEL="local:7b")
    client = build_llm_for_model(config, "local:8b", task=task)
    assert isinstance(client, OpenRouterFreeLLM)
    assert client._models[0] == getattr(config, field)
    assert client._models[-1] == "openrouter/free"


def test_provider_selection_and_embeddings():
    assert isinstance(build_llm_from_settings(settings()), OpenRouterFreeLLM)
    local = build_llm_from_settings(settings(LLM_PROVIDER="compatible"))
    assert type(local) is OpenAICompatibleLLM
    no_key = settings(OPENROUTER_API_KEY="")
    assert type(build_llm_from_settings(no_key)) is OpenAICompatibleLLM
    assert build_llm_from_settings(settings(LLM_ENABLED=False)) is None
    assert build_embedding_llm_from_settings(settings()) is None
    assert type(build_embedding_llm_from_settings(no_key)) is OpenAICompatibleLLM


def test_lowercase_env_key_is_loaded(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    env = tmp_path / ".env"
    env.write_text("openrouter_api_key=test-only\n", encoding="utf-8")
    assert Settings(_env_file=env).openrouter_api_key == "test-only"


@pytest.mark.parametrize("models", [[], ["paid/model"], ["a/model:free", "paid/model"]])
def test_paid_models_are_rejected(models):
    with pytest.raises(ValueError, match=":free"):
        OpenRouterFreeLLM(api_key="test", models=models, task="analysis")


def test_explicit_openrouter_requires_key():
    config = settings(OPENROUTER_API_KEY="", LLM_PROVIDER="openrouter")
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        build_llm_from_settings(config)


@pytest.mark.asyncio
@pytest.mark.parametrize("task", ["extraction", "reasoning", "writer"])
async def test_request_contract_and_actual_fallback_model(monkeypatch, task):
    def handler(request):
        assert str(request.url) == "https://openrouter.ai/api/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-key"
        body = json.loads(request.content)
        assert body["provider"]["max_price"] == {"prompt": 0, "completion": 0, "request": 0}
        assert all(m.endswith(":free") or m == "openrouter/free" for m in body["models"])
        assert body["max_tokens"] > 0
        assert ("response_format" in body) == (task != "writer")
        assert body["reasoning"]["exclude"] is True
        assert body["messages"][1]["content"] == "synthetic data"
        return httpx.Response(200, json={
            "model": "actual/fallback:free",
            "choices": [{"message": {"content": '{"ok": true}'}, "finish_reason": "stop"}],
        })
    mock_http(monkeypatch, handler)
    client = build_llm_from_settings(settings(), task=task)
    assert await client.complete("Return JSON", "synthetic data") == '{"ok": true}'
    assert client.last_model == "actual/fallback:free"


@pytest.mark.asyncio
async def test_rate_limit_cooldown_is_shared_across_tasks(monkeypatch):
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(429, headers={"Retry-After": "120"})
    mock_http(monkeypatch, handler)
    with pytest.raises(httpx.HTTPStatusError):
        await build_llm_from_settings(settings(), task="extraction").complete("s", "u")
    with pytest.raises(LLMUnavailableError):
        await build_llm_from_settings(settings(), task="reasoning").complete("s", "u")
    assert len(requests) == 1
    module._UNAVAILABLE_UNTIL["https://openrouter.ai/api/v1"] = 0
    with pytest.raises(httpx.HTTPStatusError):
        await build_llm_from_settings(settings()).complete("s", "u")
    assert len(requests) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("content,finish", [(None, "stop"), ("", "stop"), ("{}", "length"), ("nonsense", "stop")])
async def test_unusable_completions_fail_for_deterministic_fallback(monkeypatch, content, finish):
    mock_http(monkeypatch, lambda request: httpx.Response(200, json={
        "choices": [{"message": {"content": content}, "finish_reason": finish}],
    }))
    with pytest.raises(ValueError):
        await build_llm_from_settings(settings()).complete("s", "u")


@pytest.mark.asyncio
async def test_openrouter_embeddings_never_make_a_request(monkeypatch):
    def no_network(request):
        pytest.fail("Free chat must not send paid embedding requests")
    mock_http(monkeypatch, no_network)
    with pytest.raises(NotImplementedError):
        await build_llm_from_settings(settings()).embed(["text"], "paid/embedder")


def completion_response():
    return httpx.Response(200, json={
        "model": "served/model:free",
        "choices": [{"message": {"content": '{"ok": true}'}, "finish_reason": "stop"}],
    })


@pytest.mark.asyncio
async def test_cache_reuses_across_clients_but_isolates_inputs_and_credentials(monkeypatch):
    calls = []
    mock_http(monkeypatch, lambda request: (calls.append(request), completion_response())[1])
    first = build_llm_from_settings(settings())
    await first.complete("system", "user")
    repeated = build_llm_from_settings(settings())
    assert await repeated.complete("system", "user") == '{"ok": true}'
    assert repeated.last_model == "served/model:free"
    assert len(calls) == 1
    await repeated.complete("system", "changed facts")
    await build_llm_from_settings(settings(OPENROUTER_API_KEY="other-key")).complete("system", "user")
    assert len(calls) == 3
    await repeated.complete("system", "user", temperature=0.5)
    await repeated.complete("system", "user", temperature=0.5)
    assert len(calls) == 5


@pytest.mark.asyncio
async def test_duplicate_requests_share_work_and_survive_waiter_cancellation(monkeypatch):
    entered, release = asyncio.Event(), asyncio.Event()
    calls = []
    async def handler(request):
        calls.append(request)
        entered.set()
        await release.wait()
        return completion_response()
    mock_http(monkeypatch, handler)
    clients = [build_llm_from_settings(settings()) for _ in range(8)]
    tasks = [asyncio.create_task(c.complete("s", "same")) for c in clients]
    await asyncio.wait_for(entered.wait(), 1)
    tasks[0].cancel()
    with pytest.raises(asyncio.CancelledError):
        await tasks[0]
    release.set()
    assert await asyncio.gather(*tasks[1:]) == ['{"ok": true}'] * 7
    assert len(calls) == 1
    assert all(c.last_model == "served/model:free" for c in clients[1:])


@pytest.mark.asyncio
async def test_expiry_and_disabled_cache(monkeypatch):
    calls = []
    mock_http(monkeypatch, lambda request: (calls.append(request), completion_response())[1])
    client = build_llm_from_settings(settings(OPENROUTER_CACHE_TTL_SECONDS=0.01))
    await client.complete("s", "u")
    await asyncio.sleep(0.02)
    await client.complete("s", "u")
    assert len(calls) == 2
    disabled = build_llm_from_settings(settings(OPENROUTER_CACHE_TTL_SECONDS=0))
    await disabled.complete("s", "u")
    await disabled.complete("s", "u")
    assert len(calls) == 4


@pytest.mark.asyncio
async def test_bad_responses_are_not_cached(monkeypatch):
    calls = []
    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(200, json={"choices": []})
        return completion_response()
    mock_http(monkeypatch, handler)
    client = build_llm_from_settings(settings())
    with pytest.raises(ValueError):
        await client.complete("s", "u")
    assert await client.complete("s", "u") == '{"ok": true}'
    await client.complete("s", "u")
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_total_deadline_and_shutdown_cancel_pending_work(monkeypatch):
    stopped = asyncio.Event()
    async def handler(request):
        try:
            await asyncio.Event().wait()
        finally:
            stopped.set()
    mock_http(monkeypatch, handler)
    client = build_llm_from_settings(settings(OPENROUTER_TIMEOUT_SECONDS=0.02))
    with pytest.raises(LLMUnavailableError, match="time budget"):
        await client.complete("s", "u")
    await asyncio.wait_for(stopped.wait(), 1)
    from backend.shared.llm_runtime import get_llm_runtime
    runtime = get_llm_runtime()
    assert not runtime.pending
    await close_llm_runtime()
    assert runtime.http.is_closed


@pytest.mark.asyncio
async def test_global_concurrency_is_bounded_and_pool_is_reused(monkeypatch):
    full, release = asyncio.Event(), asyncio.Event()
    active = peak = calls = 0
    async def handler(request):
        nonlocal active, peak, calls
        calls += 1
        active += 1
        peak = max(peak, active)
        if active == 3:
            full.set()
        await release.wait()
        active -= 1
        return completion_response()
    original = httpx.AsyncClient
    created = []
    def create(**kwargs):
        client = original(transport=httpx.MockTransport(handler), **kwargs)
        created.append(client)
        return client
    monkeypatch.setattr(module.httpx, "AsyncClient", create)
    tasks = [asyncio.create_task(build_llm_from_settings(settings()).complete("s", str(i))) for i in range(8)]
    await asyncio.wait_for(full.wait(), 1)
    assert calls == 3
    release.set()
    await asyncio.gather(*tasks)
    assert calls == 8
    assert peak == 3
    assert len(created) == 1


@pytest.mark.asyncio
async def test_cache_size_is_bounded(monkeypatch):
    from backend.shared.llm_runtime import get_llm_runtime
    mock_http(monkeypatch, lambda request: completion_response())
    client = build_llm_from_settings(settings())
    for i in range(260):
        await client.complete("s", str(i))
    assert len(get_llm_runtime().cache) == 256


@pytest.mark.asyncio
@pytest.mark.parametrize("task,budget", [
    ("extraction", 768), ("writer", 2048), ("analysis", 2048),
    ("reasoning", 6144), ("strategist", 6144), ("portfolio", 6144),
])
async def test_optimizations_preserve_context_output_and_original_budgets(monkeypatch, task, budget):
    system = "Use all provided evidence."
    evidence = "Revenue grew 10%; debt rose 20%. " * 1000
    output = json.dumps({"summary": "Full explanation. " * 500})
    calls = []

    def handler(request):
        calls.append(request)
        body = json.loads(request.content)
        assert body["messages"] == [
            {"role": "system", "content": system},
            {"role": "user", "content": evidence},
        ]
        assert body["max_tokens"] == budget
        assert "sort" not in body["provider"]
        assert body["reasoning"] == (
            {"effort": "low", "exclude": True}
            if task in {"reasoning", "strategist", "portfolio"}
            else {"enabled": False, "exclude": True}
        )
        return httpx.Response(200, json={
            "model": "served/model:free",
            "choices": [{"message": {"content": output}, "finish_reason": "stop"}],
        })

    mock_http(monkeypatch, handler)
    client = build_llm_from_settings(settings(), task=task)
    assert client._deadline == 60
    assert client._timeout.connect == 10
    assert await client.complete(system, evidence) == output
    assert await client.complete(system, evidence) == output
    assert len(calls) == 1
