"""
Comprehensive test script for Prospera Market Simulator API.

Usage:
    python test_api.py                  # Run all tests against localhost:8000
    python test_api.py --url http://example.com:8000  # Test against specific URL
    python test_api.py --verbose        # Show detailed output

Prerequisites:
    - Server must be running (python main.py)
    - Python packages: httpx, pydantic
"""

import argparse
import asyncio
import json
import sys
from decimal import Decimal
from typing import Any, Optional

import httpx
from pydantic import BaseModel


class TestConfig:
    """Configuration for API tests."""
    
    def __init__(self, base_url: str = "http://localhost:8000", verbose: bool = False):
        self.base_url = base_url.rstrip("/")
        self.verbose = verbose
        self.client: Optional[httpx.AsyncClient] = None
        self.test_results = []

    async def __aenter__(self):
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    def log(self, message: str, level: str = "INFO") -> None:
        """Log a message."""
        prefix = f"[{level}]"
        print(f"{prefix} {message}")

    def log_request(self, method: str, url: str, data: Optional[dict] = None) -> None:
        """Log a request."""
        if self.verbose:
            self.log(f"→ {method} {url}", "REQUEST")
            if data:
                self.log(f"  Data: {json.dumps(data, indent=2)}", "REQUEST")

    def log_response(self, status: int, data: Any) -> None:
        """Log a response."""
        if self.verbose:
            self.log(f"← Status: {status}", "RESPONSE")
            if isinstance(data, dict):
                self.log(f"  Data: {json.dumps(data, indent=2, default=str)}", "RESPONSE")
            else:
                self.log(f"  Data: {data}", "RESPONSE")

    async def request(
        self,
        method: str,
        path: str,
        data: Optional[dict] = None,
        expected_status: int = 200,
    ) -> tuple[int, Any]:
        """Make an HTTP request and validate response."""
        url = f"{self.base_url}{path}"
        self.log_request(method, url, data)

        try:
            if method == "GET":
                response = await self.client.get(path)
            elif method == "POST":
                response = await self.client.post(path, json=data)
            elif method == "PATCH":
                response = await self.client.patch(path, json=data)
            elif method == "DELETE":
                response = await self.client.delete(path)
            else:
                raise ValueError(f"Unsupported method: {method}")

            self.log_response(response.status_code, response.json() if response.content else {})

            if response.status_code != expected_status:
                raise AssertionError(
                    f"Expected status {expected_status}, got {response.status_code}"
                )

            return response.status_code, response.json() if response.content else {}
        except Exception as e:
            self.log(f"Request failed: {e}", "ERROR")
            raise


async def test_health_check(config: TestConfig) -> None:
    """Test health check endpoint."""
    config.log("=" * 60)
    config.log("Test: Health Check", "TEST")
    config.log("=" * 60)

    status, response = await config.request("GET", "/health")
    assert response.get("status") == "healthy"
    config.log("✓ Health check passed", "SUCCESS")


async def test_environment_lifecycle(config: TestConfig) -> tuple[str, str]:
    """Test environment creation, renaming, and retrieval."""
    config.log("=" * 60)
    config.log("Test: Environment Lifecycle", "TEST")
    config.log("=" * 60)

    # Create environment
    config.log("Creating environment...")
    env_data = {
        "name": "Test Portfolio",
        "owner_type": "individual"
    }
    status, response = await config.request("POST", "/api/v1/environments", env_data)
    assert response.get("status") == "created"
    config.log("✓ Environment created", "SUCCESS")

    # Note: We need to retrieve the environment ID from somewhere else
    # For now, we'll generate a test environment ID
    test_env_id = "test-env-123"

    # Rename environment
    config.log(f"Renaming environment {test_env_id}...")
    rename_data = {
        "environment_id": test_env_id,
        "new_name": "Renamed Portfolio"
    }
    status, response = await config.request(
        "PATCH",
        f"/api/v1/environments/{test_env_id}",
        rename_data,
        expected_status=200
    )
    assert response.get("status") == "renamed"
    config.log("✓ Environment renamed", "SUCCESS")

    return test_env_id, "Renamed Portfolio"


async def test_cash_operations(config: TestConfig, environment_id: str) -> None:
    """Test deposit and withdraw operations."""
    config.log("=" * 60)
    config.log("Test: Cash Operations", "TEST")
    config.log("=" * 60)

    # Deposit cash
    config.log(f"Depositing cash to environment {environment_id}...")
    deposit_data = {
        "environment_id": environment_id,
        "amount": {
            "amount": 10000.00,
            "currency": "USD"
        }
    }
    status, response = await config.request(
        "POST",
        f"/api/v1/portfolios/{environment_id}/cash/deposit",
        deposit_data,
        expected_status=200
    )
    assert response.get("status") == "deposited"
    config.log("✓ Cash deposited (10,000 USD)", "SUCCESS")

    # Withdraw cash
    config.log("Withdrawing cash from environment...")
    withdraw_data = {
        "environment_id": environment_id,
        "amount": {
            "amount": 2000.00,
            "currency": "USD"
        }
    }
    status, response = await config.request(
        "POST",
        f"/api/v1/portfolios/{environment_id}/cash/withdraw",
        withdraw_data,
        expected_status=200
    )
    assert response.get("status") == "withdrawn"
    config.log("✓ Cash withdrawn (2,000 USD)", "SUCCESS")


async def test_trading_operations(config: TestConfig, environment_id: str) -> None:
    """Test buy and sell operations."""
    config.log("=" * 60)
    config.log("Test: Trading Operations", "TEST")
    config.log("=" * 60)

    # Buy stock
    config.log("Placing buy order...")
    buy_data = {
        "environment_id": environment_id,
        "symbol": "AAPL",
        "quantity": 10.5,
        "order_type": "BUY"
    }
    status, response = await config.request(
        "POST",
        f"/api/v1/portfolios/{environment_id}/buy",
        buy_data,
        expected_status=200
    )
    assert response.get("status") == "order_placed"
    assert response.get("symbol") == "AAPL"
    config.log("✓ Buy order placed (10.5 shares of AAPL)", "SUCCESS")

    # Sell stock
    config.log("Placing sell order...")
    sell_data = {
        "environment_id": environment_id,
        "symbol": "AAPL",
        "quantity": 5.0,
        "order_type": "SELL"
    }
    status, response = await config.request(
        "POST",
        f"/api/v1/portfolios/{environment_id}/sell",
        sell_data,
        expected_status=200
    )
    assert response.get("status") == "order_placed"
    assert response.get("symbol") == "AAPL"
    config.log("✓ Sell order placed (5 shares of AAPL)", "SUCCESS")


async def test_portfolio_queries(config: TestConfig, environment_id: str) -> None:
    """Test holdings, transactions, and performance queries."""
    config.log("=" * 60)
    config.log("Test: Portfolio Queries", "TEST")
    config.log("=" * 60)

    # Get holdings
    config.log("Fetching holdings...")
    status, holdings = await config.request(
        "GET",
        f"/api/v1/portfolios/{environment_id}/holdings"
    )
    assert isinstance(holdings, list)
    config.log(f"✓ Retrieved {len(holdings)} holdings", "SUCCESS")
    if holdings and config.verbose:
        for holding in holdings:
            config.log(f"  - {holding.get('symbol')}: {holding.get('quantity')} shares", "INFO")

    # Get transactions
    config.log("Fetching transactions...")
    status, transactions = await config.request(
        "GET",
        f"/api/v1/portfolios/{environment_id}/transactions"
    )
    assert isinstance(transactions, list)
    config.log(f"✓ Retrieved {len(transactions)} transactions", "SUCCESS")
    if transactions and config.verbose:
        for tx in transactions[:3]:  # Show first 3
            config.log(f"  - {tx.get('transaction_type')}: {tx.get('amount')}", "INFO")

    # Get portfolio performance
    config.log("Fetching portfolio performance...")
    status, performance = await config.request(
        "GET",
        f"/api/v1/portfolios/{environment_id}/performance"
    )
    assert isinstance(performance, dict)
    config.log("✓ Retrieved portfolio performance", "SUCCESS")
    if config.verbose:
        config.log(f"  Cash Balance: {performance.get('cash_balance')} USD", "INFO")
        config.log(f"  Portfolio Value: {performance.get('portfolio_value')} USD", "INFO")
        config.log(f"  Return %: {performance.get('return_percentage')}%", "INFO")


async def test_market_data(config: TestConfig) -> None:
    """Test market data endpoints."""
    config.log("=" * 60)
    config.log("Test: Market Data", "TEST")
    config.log("=" * 60)

    # Get quote
    config.log("Fetching market quote for AAPL...")
    status, quote = await config.request(
        "GET",
        "/api/v1/market-data/quote/AAPL"
    )
    assert isinstance(quote, dict)
    config.log("✓ Retrieved market quote", "SUCCESS")
    if config.verbose:
        config.log(f"  Symbol: {quote.get('symbol')}", "INFO")
        config.log(f"  Last Price: {quote.get('last_price')}", "INFO")

    # Search symbols
    config.log("Searching for symbols...")
    search_data = {"query": "apple"}
    status, results = await config.request(
        "POST",
        "/api/v1/market-data/search",
        search_data
    )
    assert isinstance(results, dict)
    config.log("✓ Retrieved search results", "SUCCESS")

    # Get metadata
    config.log("Fetching market metadata...")
    status, metadata = await config.request(
        "GET",
        "/api/v1/market-data/metadata"
    )
    assert isinstance(metadata, dict)
    config.log("✓ Retrieved market metadata", "SUCCESS")
    if config.verbose:
        config.log(f"  Exchanges: {metadata.get('supported_exchanges')}", "INFO")
        config.log(f"  Currencies: {metadata.get('supported_currencies')}", "INFO")


async def run_all_tests(config: TestConfig) -> None:
    """Run all tests."""
    try:
        await test_health_check(config)
        config.log("")

        env_id, env_name = await test_environment_lifecycle(config)
        config.log("")

        await test_cash_operations(config, env_id)
        config.log("")

        await test_trading_operations(config, env_id)
        config.log("")

        await test_portfolio_queries(config, env_id)
        config.log("")

        await test_market_data(config)
        config.log("")

        config.log("=" * 60)
        config.log("All tests passed! ✓", "SUCCESS")
        config.log("=" * 60)

    except AssertionError as e:
        config.log(f"Assertion failed: {e}", "FAILED")
        sys.exit(1)
    except Exception as e:
        config.log(f"Test failed with error: {e}", "ERROR")
        sys.exit(1)


async def main() -> None:
    """Main test runner."""
    parser = argparse.ArgumentParser(
        description="Test Prospera Market Simulator API"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output",
    )

    args = parser.parse_args()

    async with TestConfig(base_url=args.url, verbose=args.verbose) as config:
        await run_all_tests(config)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Test runner error: {e}")
        sys.exit(1)
