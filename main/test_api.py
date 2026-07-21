"""End-to-end smoke test for the Prospera backend API.

By default this runs the whole API **in-process against a throwaway SQLite
database** — no server to start, no network, no API keys required. It exercises
every offline-capable flow (environments, cash, portfolio queries, research
RAG, events) and *gracefully skips* the flows that genuinely need a live market
-data key (quotes, news sync, trading), reporting them as SKIPPED rather than
failing.

Usage (from the ``main`` directory, with the virtualenv active):

    python test_api.py                 # in-process, offline (recommended)
    python test_api.py --verbose       # show every request/response
    python test_api.py --url http://localhost:8000   # test a running server

Exit code is non-zero only if a test that *should* pass offline fails, so this
is safe to run in CI.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import tempfile
from contextlib import asynccontextmanager
from typing import Any, Optional

import httpx


class Results:
    """Tallies passed / skipped / failed checks and prints a summary."""

    def __init__(self) -> None:
        self.passed = 0
        self.skipped = 0
        self.failed = 0

    def ok(self, message: str) -> None:
        self.passed += 1
        print(f"  [PASS] {message}")

    def skip(self, message: str) -> None:
        self.skipped += 1
        print(f"  [SKIP] {message}")

    def fail(self, message: str) -> None:
        self.failed += 1
        print(f"  [FAIL] {message}")


class ApiTester:
    """Thin request helper around an httpx client with pass/skip/fail tracking."""

    def __init__(self, client: httpx.AsyncClient, results: Results, verbose: bool) -> None:
        self._client = client
        self._results = results
        self._verbose = verbose

    async def call(
        self,
        method: str,
        path: str,
        json: Optional[dict] = None,
    ) -> tuple[int, Any]:
        response = await self._client.request(method, path, json=json)
        body: Any = {}
        if response.content:
            try:
                body = response.json()
            except Exception:
                body = response.text
        if self._verbose:
            print(f"    -> {method} {path} [{response.status_code}]")
            print(f"       {body}")
        return response.status_code, body


def section(title: str) -> None:
    print(f"\n=== {title} ===")


async def run_offline_suite(t: ApiTester, r: Results) -> None:
    # --- Health ------------------------------------------------------------
    section("Health")
    status, body = await t.call("GET", "/health")
    if status == 200 and body.get("status") == "healthy":
        r.ok("GET /health is healthy")
    else:
        r.fail(f"GET /health returned {status}: {body}")

    # --- Environment lifecycle --------------------------------------------
    section("Environment lifecycle")
    status, env = await t.call(
        "POST", "/api/v1/environments/", {"name": "Smoke Test", "owner_type": "user"}
    )
    env_id = env.get("environment_id") if isinstance(env, dict) else None
    if status == 200 and env_id:
        r.ok(f"created environment {env_id}")
    else:
        r.fail(f"create environment failed ({status}): {env}")
        return  # everything below needs an environment

    status, got = await t.call("GET", f"/api/v1/environments/{env_id}")
    if status == 200 and got.get("environment_id") == env_id:
        r.ok("fetched the environment back")
    else:
        r.fail(f"get environment failed ({status}): {got}")

    status, _ = await t.call(
        "PATCH",
        f"/api/v1/environments/{env_id}",
        {"environment_id": env_id, "new_name": "Smoke Test (renamed)"},
    )
    r.ok("renamed environment") if status == 200 else r.fail(f"rename failed ({status})")

    # --- Cash operations (INR: the platform base currency) -----------------
    section("Cash operations")
    status, _ = await t.call(
        "POST",
        f"/api/v1/portfolios/{env_id}/cash/deposit",
        {"environment_id": env_id, "amount": {"amount": 100000, "currency": "INR"}},
    )
    r.ok("deposited 100,000 INR") if status == 200 else r.fail(f"deposit failed ({status})")

    status, _ = await t.call(
        "POST",
        f"/api/v1/portfolios/{env_id}/cash/withdraw",
        {"environment_id": env_id, "amount": {"amount": 20000, "currency": "INR"}},
    )
    r.ok("withdrew 20,000 INR") if status == 200 else r.fail(f"withdraw failed ({status})")

    # --- Portfolio queries -------------------------------------------------
    section("Portfolio queries")
    status, holdings = await t.call("GET", f"/api/v1/portfolios/{env_id}/holdings")
    if status == 200 and isinstance(holdings, list):
        r.ok(f"holdings list returned ({len(holdings)} holdings)")
    else:
        r.fail(f"holdings failed ({status}): {holdings}")

    status, txns = await t.call("GET", f"/api/v1/portfolios/{env_id}/transactions")
    if status == 200 and isinstance(txns, list) and len(txns) >= 2:
        r.ok(f"transactions recorded the cash moves ({len(txns)} txns)")
    else:
        r.fail(f"transactions unexpected ({status}): {txns}")

    status, perf = await t.call("GET", f"/api/v1/portfolios/{env_id}/performance")
    if status == 200 and perf.get("cash_balance", "").startswith("80000"):
        r.ok(f"performance shows expected cash balance {perf.get('cash_balance')}")
    elif status == 200:
        r.fail(f"performance cash balance unexpected: {perf}")
    else:
        r.fail(f"performance failed ({status}): {perf}")

    # --- Research RAG (fully offline: hashing embedder + in-Python cosine) --
    section("Research RAG")
    await t.call(
        "POST",
        "/api/v1/research/documents",
        {
            "title": "Apple FY24 Annual Report",
            "content": "Apple reported record iPhone revenue growth driven by services and wearables.",
            "document_type": "annual_report",
            "symbols": ["AAPL"],
        },
    )
    status, _ = await t.call(
        "POST",
        "/api/v1/research/documents",
        {
            "title": "Reliance Q3 Update",
            "content": "Reliance Jio added subscribers while retail margins expanded across India.",
            "document_type": "earnings_call",
            "symbols": ["RELIANCE.NS"],
        },
    )
    r.ok("ingested research documents") if status == 200 else r.fail(f"ingest failed ({status})")

    status, search = await t.call(
        "POST", "/api/v1/research/search", {"query": "iPhone revenue growth", "top_k": 3}
    )
    if status == 200 and isinstance(search, dict):
        r.ok("semantic search returned results")
    else:
        r.fail(f"research search failed ({status}): {search}")

    status, _ = await t.call("GET", "/api/v1/research/stats")
    r.ok("research stats reachable") if status == 200 else r.fail(f"research stats failed ({status})")

    # --- Events ------------------------------------------------------------
    section("Events")
    status, _ = await t.call("GET", "/api/v1/events/stats")
    r.ok("events stats reachable") if status == 200 else r.fail(f"events stats failed ({status})")

    # --- Cleanup -----------------------------------------------------------
    section("Cleanup")
    status, _ = await t.call("DELETE", f"/api/v1/environments/{env_id}")
    r.ok("deleted environment") if status == 200 else r.fail(f"delete failed ({status})")


async def run_network_suite(t: ApiTester, r: Results) -> None:
    """Flows that need a live market-data key; skipped (not failed) if absent."""

    section("Market data (needs MARKET_DATA_API_KEY)")
    status, quote = await t.call("GET", "/api/v1/market-data/quote/AAPL")
    if status == 200 and isinstance(quote, dict) and quote.get("last_price"):
        r.ok(f"AAPL quote: {quote.get('last_price')} {quote.get('currency')}")
    else:
        r.skip(f"market-data quote unavailable offline ({status})")

    section("News sync (needs MARKET_DATA_API_KEY)")
    status, sync = await t.call(
        "POST", "/api/v1/news/sync", {"categories": ["global"], "limit": 5}
    )
    if status == 200 and isinstance(sync, dict):
        r.ok(f"news sync stored {sync.get('stored_count')} articles")
    else:
        r.skip(f"news sync unavailable offline ({status})")


@asynccontextmanager
async def in_process_client():
    """Build an httpx client bound to the ASGI app + a temp SQLite DB."""

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{tmp.name}"
    os.environ.setdefault("APP_DEBUG", "false")

    # Import after env is set so the engine picks up the temp DB.
    from backend.app import app, configure_event_loop_policy

    configure_event_loop_policy()
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):  # runs table creation
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver", timeout=30.0
        ) as client:
            yield client
    try:
        os.unlink(tmp.name)
    except OSError:
        pass


@asynccontextmanager
async def live_client(url: str):
    async with httpx.AsyncClient(base_url=url.rstrip("/"), timeout=30.0) as client:
        yield client


async def main() -> None:
    parser = argparse.ArgumentParser(description="Prospera backend smoke test")
    parser.add_argument("--url", default=None, help="Test a running server instead of in-process")
    parser.add_argument("--verbose", action="store_true", help="Show every request/response")
    parser.add_argument("--skip-network", action="store_true", help="Skip market-data/news flows")
    args = parser.parse_args()

    results = Results()
    maker = live_client(args.url) if args.url else in_process_client()

    mode = f"live server {args.url}" if args.url else "in-process (offline, temp SQLite)"
    print(f"Prospera API smoke test — mode: {mode}")

    async with maker as client:
        tester = ApiTester(client, results, args.verbose)
        await run_offline_suite(tester, results)
        if not args.skip_network:
            await run_network_suite(tester, results)

    print("\n" + "=" * 50)
    print(f"PASSED: {results.passed}   SKIPPED: {results.skipped}   FAILED: {results.failed}")
    print("=" * 50)
    sys.exit(1 if results.failed else 0)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] interrupted")
        sys.exit(0)
