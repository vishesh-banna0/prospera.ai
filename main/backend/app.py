from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.router import create_api_router
from backend.core.config import get_settings
from backend.core.exceptions import ProsperaError

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""

    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="Prospera Market Simulator API",
        version="0.1.0",
        debug=settings.app_debug,
    )

    register_middlewares(app)
    register_exception_handlers(app)

    api_router = create_api_router()
    app.include_router(api_router)

    @app.get("/health")
    async def health_check() -> dict:
        return {
            "status": "healthy",
            "app": settings.app_name,
        }

    @app.on_event("startup")
    async def startup_event() -> None:
        logger.info(
            f"Starting {settings.app_name} in {settings.app_env} environment"
        )

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        logger.info(f"Shutting down {settings.app_name}")

    return app


def register_middlewares(app: FastAPI) -> None:
    """Register application middleware."""

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers."""

    @app.exception_handler(ProsperaError)
    async def prospera_exception_handler(
        request: Request,
        exc: ProsperaError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={
                "detail": str(exc),
                "error_code": exc.__class__.__name__,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.error(
            f"Unhandled exception: {exc}",
            exc_info=True,
        )

        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
            },
        )


app = create_app()


"""
Purpose:
Define the backend application entry point for Prospera.

Responsibilities:
- Create the FastAPI application instance
- Register routers from the API layer
- Load core configuration and shared middleware
- Wire startup and shutdown lifecycle hooks
- Handle exceptions globally

Dependencies:
- backend.core.config (settings)
- backend.api.router (API router factory)
- FastAPI framework

Functions:
- create_app: Factory function to create configured FastAPI instance
- register_middlewares: Configure CORS and other middleware
- register_exception_handlers: Set up global error handling

Middleware:
- CORS: Allow cross-origin requests (configurable)

ExceptionHandlers:
- ProsperaError: Domain-specific exceptions
- Exception: Catch-all for unhandled exceptions

Lifecycle Hooks:
- startup_event: Log application startup
- shutdown_event: Log application shutdown

What Should Not Live Here:
- Route implementation details
- Simulator business rules
- Market data provider logic
"""