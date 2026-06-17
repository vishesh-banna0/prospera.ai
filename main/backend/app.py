from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging

from backend.core.config import get_settings
from backend.api.router import create_api_router
from backend.core.exceptions import ProsperoException

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
    
    # Register middleware
    register_middlewares(app, settings)
    
    # Register exception handlers
    register_exception_handlers(app)
    
    # Register routers
    api_router = create_api_router()
    app.include_router(api_router)
    
    # Add health check endpoint
    @app.get("/health")
    async def health_check() -> dict:
        return {"status": "healthy", "app": settings.app_name}
    
    # Lifecycle hooks
    @app.on_event("startup")
    async def startup_event():
        logger.info(f"Starting {settings.app_name} in {settings.app_env} environment")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info(f"Shutting down {settings.app_name}")
    
    return app


def register_middlewares(app: FastAPI, settings) -> None:
    """Register application middleware."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: Configure based on settings
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers."""
    
    @app.exception_handler(ProsperoException)
    async def prospero_exception_handler(
        request: Request,
        exc: ProsperoException,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc), "error_code": exc.__class__.__name__},
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )


# Application entry point
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
- ProsperoException: Domain-specific exceptions
- Exception: Catch-all for unhandled exceptions

Lifecycle Hooks:
- startup_event: Log application startup
- shutdown_event: Log application shutdown

What Should Not Live Here:
- Route implementation details
- Simulator business rules
- Market data provider logic
"""
