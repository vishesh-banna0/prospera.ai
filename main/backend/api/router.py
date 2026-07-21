from __future__ import annotations

from fastapi import APIRouter

from backend.api.routes import (
    environments,
    portfolios,
    market_data,
    news,
    events,
    research,
    company,
    prediction,
    signals,
    reasoning,
)


def create_api_router() -> APIRouter:
    """Create and configure the top-level API router."""
    api_router = APIRouter(prefix="/api/v1")

    # Register route groups
    api_router.include_router(environments.router)
    api_router.include_router(portfolios.router)
    api_router.include_router(market_data.router)
    api_router.include_router(news.router)
    api_router.include_router(events.router)
    api_router.include_router(research.router)
    api_router.include_router(company.router)
    api_router.include_router(prediction.router)
    api_router.include_router(signals.router)
    api_router.include_router(reasoning.router)

    return api_router


"""
Purpose:
Define the top-level API router composition for backend endpoints.

Responsibilities:
- Register route groups for environments, portfolios, and market data
- Keep route versioning and prefix strategy consistent
- Provide a single place to assemble API modules into application

Dependencies:
- backend.api.routes.environments
- backend.api.routes.portfolios
- backend.api.routes.market_data

Functions:
- create_api_router: Factory function to create configured router

Route Groups (all under /api/v1 prefix):
- /environments: Environment lifecycle
- /portfolios: Portfolio and trading operations
- /market-data: Market data access

What Should Not Live Here:
- Endpoint implementation details
- Validation rules (belong in DTOs)
- Business workflow logic
"""
