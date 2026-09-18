"""Load the starter financial corpus into the research knowledge base.

The passages themselves live in
``backend/modules/research/application/seed_corpus.py`` — keeping them in the
package (rather than in this script) means they are importable and covered by
the test suite, not just runnable.

Usage (from the ``main`` directory, with the virtualenv active):

    python scripts/seed_research.py

Requires the database to be reachable (DATABASE_URL in your .env). Re-running
is safe: ingestion is keyed on a content hash, so unchanged passages replace
themselves instead of duplicating.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Make ``backend`` importable when this file is run directly as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.api.dependencies import build_research_repository  # noqa: E402
from backend.app import configure_event_loop_policy  # noqa: E402
from backend.core.config import get_settings  # noqa: E402
from backend.core.database import (  # noqa: E402
    create_all_tables,
    dispose_engine,
    get_session_maker,
)
from backend.modules.research.application.seed_corpus import SEED_CORPUS  # noqa: E402
from backend.modules.research.application.services import ResearchService  # noqa: E402
from backend.modules.research.infrastructure.providers import (  # noqa: E402
    HashingEmbedder,
    LLMEmbedder,
    PlainTextParser,
)
from backend.shared.llm import build_embedding_llm_from_settings  # noqa: E402


async def _main() -> None:
    settings = get_settings()
    print(f"Seeding research knowledge base in: {settings.database_url}")
    await create_all_tables()

    llm = build_embedding_llm_from_settings(settings)
    embedder = (
        LLMEmbedder(
            llm,
            model=settings.llm_embedding_model,
            fallback=HashingEmbedder(),
        )
        if llm is not None
        else HashingEmbedder()
    )
    print(f"Embedder: {embedder.name}")

    session_maker = get_session_maker()
    ingested = 0
    chunks = 0
    async with session_maker() as session:
        service = ResearchService(
            repository=build_research_repository(session),
            embedder=embedder,
            parser=PlainTextParser(),
            commit=session.commit,
        )
        for request in SEED_CORPUS:
            result = await service.ingest_document(request)
            ingested += 1
            chunks += result.chunk_count
            print(
                f"  [{ingested:2d}/{len(SEED_CORPUS)}] {request.title} "
                f"({result.chunk_count} chunks)"
            )

        stats = await service.get_stats()

    await dispose_engine()
    print(
        f"\nDone. Seeded {ingested} documents / {chunks} chunks. "
        f"Store now holds {stats.total_documents} documents "
        f"and {stats.total_chunks} chunks."
    )
    if embedder.name == "hashing-v1":
        print(
            "\nNote: embedded with the deterministic hashing embedder (lexical "
            "matching). Start your LLM endpoint and re-run to embed "
            "semantically — vectors from different embedders are not "
            "comparable, so a re-run is required, not optional."
        )


if __name__ == "__main__":
    configure_event_loop_policy()
    asyncio.run(_main())
