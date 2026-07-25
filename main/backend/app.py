from __future__ import annotations

import asyncio
import sys
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.router import create_api_router
from backend.core.config import get_settings
from backend.core.exceptions import ProsperaError
from backend.core.logging import configure_logging, get_logger, request_id_var

logger = get_logger(__name__)


def configure_event_loop_policy() -> None:
    """Use an async DB-compatible event loop on Windows."""

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


configure_event_loop_policy()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""

    settings = get_settings()
    configure_logging(settings.log_level)

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
        if settings.db_auto_create:
            try:
                from backend.core.database import create_all_tables

                await create_all_tables()
            except Exception as exc:  # best-effort: don't block boot on DB
                logger.warning(
                    "Could not auto-create database tables on startup "
                    "(the app will still start; DB-backed endpoints may fail "
                    "until the database is reachable): %s",
                    exc,
                )

        # Keep the news warehouse fresh on a timer (see NEWS_AUTO_SYNC_* config).
        # Runs as a detached background task so it never delays boot or requests.
        if settings.news_auto_sync_enabled:
            from backend.modules.news.application.auto_sync import (
                run_news_auto_sync_loop,
            )

            app.state.news_sync_task = asyncio.create_task(run_news_auto_sync_loop())

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        logger.info(f"Shutting down {settings.app_name}")

        news_sync_task = getattr(app.state, "news_sync_task", None)
        if news_sync_task is not None:
            news_sync_task.cancel()
            try:
                await news_sync_task
            except asyncio.CancelledError:
                pass

        from backend.core.database import dispose_engine

        await dispose_engine()

    return app


def register_middlewares(app: FastAPI) -> None:
    """Register application middleware."""

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        """Give each request a short id, log it, and time it.

        The id is stored in a contextvar so every log line emitted while
        handling the request is tagged with it, and returned in the
        ``X-Request-ID`` response header for client-side correlation.
        """

        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:8]
        token = request_id_var.set(request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s -> %s (%.1f ms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        response.headers["X-Request-ID"] = request_id
        return response

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
