# Prospera Market Simulator API

Comprehensive REST API for the Prospera financial simulator platform. This API provides endpoints to create isolated portfolio environments, execute trades, manage cash, and retrieve portfolio analytics.

## Quick Start

### 1. Install Dependencies

```bash
# From the main directory
pip install -r requirements.txt
pip install uvicorn httpx pytest pytest-asyncio
```

### 2. Configure Environment

Create a `.env` file in the `main` directory with the following:

```env
# Application Configuration
APP_NAME=Prospera
APP_ENV=development
APP_DEBUG=true
APP_HOST=127.0.0.1
APP_PORT=8000

# Database Configuration
DATABASE_URL=sqlite+aiosqlite:///./prospera.db

# Market Data Configuration
MARKET_DATA_PROVIDER=finnhub
MARKET_DATA_API_KEY=your_finnhub_api_key_here
MARKET_DATA_BASE_URL=https://finnhub.io/api/v1
```

### 3. Initialize Database

```bash
# Create database tables (if not using SQLite auto-initialization)
python -c "from backend.core.config import get_settings; print(get_settings().database_url)"
```

### 4. Run the Server

```bash
# Development server with auto-reload
python main.py --reload

# Production server
python main.py --workers 4

# Specific configuration
python main.py --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

Interactive API documentation: `http://localhost:8000/docs`

### 5. Test the API

```bash
# Run comprehensive test suite
python test_api.py --verbose

# Test against specific server
python test_api.py --url http://example.com:8000

# Test without verbose output
python test_api.py
```

## API Endpoints

### Health Check

```bash
GET /health
```

Returns server status and application name.

### Environments

#### Create Environment

```bash
POST /api/v1/environments
Content-Type: application/json

{
  "name": "My Portfolio",
  "owner_type": "individual"
}
```

Response:
```json
{
  "status": "created",
  "message": "Environment created successfully"
}
```

#### Rename Environment

```bash
PATCH /api/v1/environments/{environment_id}
Content-Type: application/json

{
  "environment_id": "env-123",
  "new_name": "Updated Portfolio Name"
}
```

#### Delete Environment

```bash
DELETE /api/v1/environments/{environment_id}
```

### Portfolio Management

#### Deposit Cash

```bash
POST /api/v1/portfolios/{environment_id}/cash/deposit
Content-Type: application/json

{
  "environment_id": "env-123",
  "amount": {
    "amount": 10000.00,
    "currency": "USD"
  }
}
```

#### Withdraw Cash

```bash
POST /api/v1/portfolios/{environment_id}/cash/withdraw
Content-Type: application/json

{
  "environment_id": "env-123",
  "amount": {
    "amount": 2000.00,
    "currency": "USD"
  }
}
```

### Trading

#### Buy Stock

```bash
POST /api/v1/portfolios/{environment_id}/buy
Content-Type: application/json

{
  "environment_id": "env-123",
  "symbol": "AAPL",
  "quantity": 10.5,
  "order_type": "BUY"
}
```

#### Sell Stock

```bash
POST /api/v1/portfolios/{environment_id}/sell
Content-Type: application/json

{
  "environment_id": "env-123",
  "symbol": "AAPL",
  "quantity": 5.0,
  "order_type": "SELL"
}
```

### Portfolio Queries

#### List Holdings

```bash
GET /api/v1/portfolios/{environment_id}/holdings
```

Response:
```json
[
  {
    "symbol": "AAPL",
    "quantity": 10.5,
    "average_cost": "150.00",
    "market_value": "1650.00",
    "unrealized_pnl": "165.00",
    "return_percentage": 11.0
  }
]
```

#### Get Transactions

```bash
GET /api/v1/portfolios/{environment_id}/transactions
```

Response:
```json
[
  {
    "transaction_id": "tx-123",
    "symbol": "AAPL",
    "transaction_type": "BUY",
    "quantity": 10.5,
    "amount": "1575.00",
    "executed_at": "2026-06-17T10:30:00"
  }
]
```

#### Get Portfolio Performance

```bash
GET /api/v1/portfolios/{environment_id}/performance
```

Response:
```json
{
  "environment_id": "env-123",
  "cash_balance": "8000.00",
  "invested_amount": "1575.00",
  "portfolio_value": "9675.00",
  "unrealized_pnl": "165.00",
  "return_percentage": 11.0
}
```

### Market Data

Prospera uses the market data service as the only internal gateway for external market providers. Finnhub powers live quote, search, and market metadata flows. yfinance powers free historical price and company-profile ingestion. Future simulator, backtesting, AI, analytics, and RL consumers should use these endpoints or the application service rather than calling providers directly.

#### Get Market Quote

```bash
GET /api/v1/market-data/quote/{symbol}
```

Response:
```json
{
  "symbol": "AAPL",
  "last_price": 157.50,
  "currency": "USD",
  "open_price": 155.00,
  "high_price": 160.00,
  "low_price": 154.50,
  "volume": 50000000,
  "as_of": "2026-06-17T16:00:00"
}
```

#### Get Historical Prices

```bash
GET /api/v1/market-data/history/AAPL?start_at=2024-01-01T00:00:00Z&end_at=2024-12-31T00:00:00Z&auto_sync=true
```

Response:
```json
{
  "symbol": "AAPL",
  "currency": "USD",
  "prices": [
    {
      "timestamp": "2024-01-02T00:00:00Z",
      "open_price": "187.15",
      "high_price": "188.44",
      "low_price": "183.89",
      "close_price": "185.64",
      "volume": 82488700,
      "adjusted_close_price": "184.73",
      "split_coefficient": null,
      "dividend_amount": null
    }
  ]
}
```

#### Sync Historical Prices

```bash
POST /api/v1/market-data/history/sync
Content-Type: application/json

{
  "symbol": "AAPL",
  "start_at": "2024-01-01T00:00:00Z",
  "end_at": "2024-12-31T00:00:00Z",
  "asset_type": "stock"
}
```

Response:
```json
{
  "symbol": "AAPL",
  "requested_start_at": "2024-01-01T00:00:00Z",
  "requested_end_at": "2024-12-31T00:00:00Z",
  "fetched_count": 252,
  "stored_count": 252,
  "skipped": false,
  "message": null
}
```

Historical synchronization is incremental. If `historical_price_bars` already contains data through the requested end date, the sync is skipped. Otherwise, the service fetches from the day after the latest stored bar and upserts rows by `(symbol, price_date)`.

#### Search Symbols

```bash
POST /api/v1/market-data/search
Content-Type: application/json

{
  "query": "apple"
}
```

#### Get Company Profile

```bash
GET /api/v1/market-data/profile/AAPL
```

Response:
```json
{
  "symbol": "AAPL",
  "instrument_name": "Apple Inc.",
  "currency": "USD",
  "exchange": "NasdaqGS",
  "asset_type": "stock",
  "sector": "Technology",
  "industry": "Consumer Electronics",
  "country": "United States",
  "website": "https://www.apple.com",
  "description": "...",
  "market_cap": "2850000000000",
  "employees": 164000
}
```

#### Get Market Metadata

```bash
GET /api/v1/market-data/metadata
```

Response:
```json
{
  "supported_exchanges": ["NYSE", "NASDAQ"],
  "supported_currencies": ["USD", "EUR"],
  "timezone": "America/New_York",
  "market_status": "open",
  "last_updated_at": "2026-06-17T16:00:00"
}
```

## Testing

### Running Tests Programmatically

```python
import asyncio
from test_api import TestConfig, run_all_tests

async def run_tests():
    async with TestConfig(base_url="http://localhost:8000", verbose=True) as config:
        await run_all_tests(config)

asyncio.run(run_tests())
```

### Using cURL

```bash
# Health check
curl http://localhost:8000/health

# Create environment
curl -X POST http://localhost:8000/api/v1/environments \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "owner_type": "individual"}'

# Deposit cash (replace {env_id})
curl -X POST http://localhost:8000/api/v1/portfolios/{env_id}/cash/deposit \
  -H "Content-Type: application/json" \
  -d '{
    "environment_id": "{env_id}",
    "amount": {"amount": 10000, "currency": "USD"}
  }'

# Buy stock
curl -X POST http://localhost:8000/api/v1/portfolios/{env_id}/buy \
  -H "Content-Type: application/json" \
  -d '{
    "environment_id": "{env_id}",
    "symbol": "AAPL",
    "quantity": 10,
    "order_type": "BUY"
  }'

# Get holdings
curl http://localhost:8000/api/v1/portfolios/{env_id}/holdings

# Get performance
curl http://localhost:8000/api/v1/portfolios/{env_id}/performance
```

## Architecture

### Application Layers

```
API Routes (HTTP endpoints)
    ↓
Service Layer (SimulatorService)
    ↓
Use Cases (Commands & Queries)
    ↓
Domain Layer (Business logic, policies)
    ↓
Infrastructure Layer (Repositories, database)
```

### Key Components

- **Commands**: Write operations (CreateEnvironment, BuyStock, etc.)
- **Queries**: Read operations (GetHoldings, GetPortfolioPerformance, etc.)
- **Repositories**: Data access layer (Environment, Holding, Transaction, etc.)
- **Policies**: Business logic functions (can_buy, calculate_cost_basis, etc.)
- **DTOs**: Data transfer objects for API contracts

### Market Data Pipeline

The Phase 6 pipeline stores provider-independent data in PostgreSQL:

- `market_instruments`: normalized symbol metadata, asset type, exchange, currency, sector, industry, and country.
- `historical_price_bars`: daily OHLCV bars, adjusted close, dividends, split coefficients, source, and unique `(symbol, price_date)`.
- `company_profiles`: normalized company metadata for company analysis and future intelligence modules.

Provider adapters must implement contracts from `backend/modules/market_data/application/providers.py` and return domain entities from `backend/modules/market_data/domain/entities.py`. The application service handles validation, incremental append behavior, deduplication through repository upserts, and API-facing response mapping.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | Prospera | Application name |
| `APP_ENV` | development | Environment (development, production, testing) |
| `APP_DEBUG` | true | Enable debug mode |
| `APP_HOST` | 127.0.0.1 | Server host |
| `APP_PORT` | 8000 | Server port |
| `DATABASE_URL` | sqlite:///./prospera.db | Database connection string |
| `MARKET_DATA_PROVIDER` | finnhub | Live quote/search/status provider |
| `MARKET_DATA_API_KEY` | - | Finnhub API key |
| `MARKET_DATA_BASE_URL` | https://finnhub.io/api/v1 | Finnhub API base URL |

## Troubleshooting

### Port Already in Use

```bash
# Find and kill process using port 8000
lsof -i :8000
kill -9 <PID>

# Or use a different port
python main.py --port 8001
```

### Database Errors

```bash
# Clear database (if using SQLite)
rm prospera.db

# Verify database URL in .env
echo $DATABASE_URL
```

### Import Errors

```bash
# Ensure you're in the main directory
cd main

# Install missing packages
pip install -r requirements.txt
```

### Connection Refused

Ensure the server is running:
```bash
python main.py --reload
```

## Development

### Code Structure

```
backend/
├── api/                          # API layer
│   ├── dependencies.py           # Dependency injection
│   ├── router.py                 # Route composition
│   └── routes/                   # Endpoint definitions
├── core/                         # Core utilities
│   ├── config.py                 # Configuration management
│   └── exceptions.py             # Custom exceptions
├── modules/                      # Business modules
│   ├── simulator/                # Portfolio simulator
│   │   ├── application/          # Use cases & services
│   │   ├── domain/               # Business logic & entities
│   │   └── infrastructure/       # Repositories & persistence
│   └── market_data/              # Market data module
├── shared/                       # Shared types & utilities
└── app.py                        # FastAPI application factory

main.py                          # Server entry point
test_api.py                      # Comprehensive test suite
```

### Adding New Endpoints

1. **Define DTOs** in `backend/modules/{module}/application/dto.py`
2. **Implement Use Cases** in `backend/modules/{module}/application/commands.py` or `queries.py`
3. **Create Routes** in `backend/api/routes/{name}.py`
4. **Register Routes** in `backend/api/router.py`
5. **Update Dependencies** in `backend/api/dependencies.py` if needed

## Performance

### Running with Multiple Workers

```bash
# Production: use 4 workers
python main.py --workers 4

# Note: Workers are disabled in reload mode
```

### Database Connection Pooling

Configure connection pooling in `backend/api/dependencies.py`:

```python
_engine = create_async_engine(
    settings.database_url,
    pool_size=20,
    max_overflow=0,
    echo=settings.app_debug,
)
```

## Next Steps

- Add scheduled market data sync jobs
- Add authentication and authorization
- Create frontend UI for portfolio management
- Add WebSocket support for real-time updates
- Implement caching strategies
- Add comprehensive logging and monitoring

## Support

For issues, questions, or contributions, please refer to the main project documentation or contact the development team.
