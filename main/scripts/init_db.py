"""Create every module's database tables from the command line.

This is the explicit, one-shot version of what the API does automatically on
startup (when DB_AUTO_CREATE=true). Use it to prepare a database without
booting the web server.

Usage (from the ``main`` directory, with the virtualenv active):

    python scripts/init_db.py

It reads DATABASE_URL from your .env (defaulting to a local SQLite file), so it
works offline out of the box and also targets PostgreSQL when configured.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Make ``backend`` importable when this file is run directly as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app import configure_event_loop_policy  # noqa: E402
from backend.core.config import get_settings  # noqa: E402
from backend.core.database import create_all_tables, dispose_engine  # noqa: E402


async def _main() -> None:
    settings = get_settings()
    print(f"Creating tables for: {settings.database_url}")
    await create_all_tables()
    await dispose_engine()
    print("Done. All module tables are ready.")


if __name__ == "__main__":
    configure_event_loop_policy()
    asyncio.run(_main())
