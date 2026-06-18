"""
Main entry point for Prospera Market Simulator API server.

Usage:
    python main.py                      # Run with default settings
    python main.py --host 0.0.0.0       # Run on all interfaces
    python main.py --port 8000          # Run on specific port
    python main.py --reload             # Run with auto-reload for development

Environment Variables:
    APP_HOST: Server host (default: 127.0.0.1)
    APP_PORT: Server port (default: 8000)
    APP_ENV: Environment (development, production, testing)
    DATABASE_URL: SQLAlchemy database URL
    APP_DEBUG: Enable debug mode (true/false)
"""

import argparse
import sys
import logging

import uvicorn

from backend.core.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Run the Prospera Market Simulator API server."""
    parser = argparse.ArgumentParser(
        description="Prospera Market Simulator API Server"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Server host (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Server port (default: 8000)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of workers (default: 1)",
    )

    args = parser.parse_args()
    settings = get_settings()

    logger.info(f"Starting Prospera API Server")
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"Debug: {settings.app_debug}")
    logger.info(f"Host: {args.host}:{args.port}")

    uvicorn.run(
        "backend.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,
        log_level="info",
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
