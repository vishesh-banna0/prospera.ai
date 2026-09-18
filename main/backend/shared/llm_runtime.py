"""Event-loop-scoped HTTP pooling and bounded reuse of free LLM completions."""
from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable

import httpx

Completion = tuple[str, str]


class LLMRuntime:
    def __init__(self) -> None:
        self.http = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=4, max_keepalive_connections=4),
        )
        self.slots = asyncio.Semaphore(3)
        self.cache: OrderedDict[str, tuple[float, Completion]] = OrderedDict()
        self.pending: dict[str, asyncio.Task[Completion]] = {}

    async def complete(
        self, key: str, generate: Callable[[], Awaitable[Completion]],
        *, ttl: float, timeout: float,
    ) -> Completion:
        now = time.monotonic()
        for expired in [k for k, (until, _) in self.cache.items() if until <= now]:
            del self.cache[expired]
        if ttl > 0 and key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key][1]
        task = self.pending.get(key)
        if task is None:
            if len(self.pending) >= 32:
                raise RuntimeError("LLM request queue is full; use deterministic fallback.")

            async def run() -> Completion:
                try:
                    # Queue time, connection, and full generation share one budget.
                    async with asyncio.timeout(timeout):
                        async with self.slots:
                            result = await generate()
                    if ttl > 0 and len(result[0]) <= 65536:
                        self.cache[key] = (time.monotonic() + ttl, result)
                        self.cache.move_to_end(key)
                        while len(self.cache) > 256:
                            self.cache.popitem(last=False)
                    return result
                finally:
                    self.pending.pop(key, None)

            task = asyncio.create_task(run())
            self.pending[key] = task
            # A disconnected waiter must not cancel other waiters or leave an
            # unobserved task exception. Generation still has a hard deadline.
            task.add_done_callback(lambda done: None if done.cancelled() else done.exception())
        async with asyncio.timeout(timeout):
            return await asyncio.shield(task)

    async def close(self) -> None:
        tasks = list(self.pending.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self.cache.clear()
        await self.http.aclose()


_RUNTIMES: dict[asyncio.AbstractEventLoop, LLMRuntime] = {}


def get_llm_runtime() -> LLMRuntime:
    loop = asyncio.get_running_loop()
    if loop not in _RUNTIMES:
        _RUNTIMES[loop] = LLMRuntime()
    return _RUNTIMES[loop]


async def close_llm_runtime() -> None:
    runtime = _RUNTIMES.pop(asyncio.get_running_loop(), None)
    if runtime is not None:
        await runtime.close()
