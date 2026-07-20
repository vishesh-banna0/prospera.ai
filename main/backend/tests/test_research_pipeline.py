from __future__ import annotations

import pytest

from backend.modules.research.application.dto import (
    DocumentQueryRequest,
    IngestDocumentRequest,
    ResearchQueryRequest,
)
from backend.modules.research.application.services import ResearchService
from backend.modules.research.domain.chunking import chunk_text
from backend.modules.research.infrastructure.providers import HashingEmbedder
from backend.modules.research.infrastructure.repositories import (
    InMemoryResearchRepository,
    _cosine_similarity,
)


def test_chunk_text_overlaps_and_covers_full_text() -> None:
    text = " ".join(f"word{i}" for i in range(400))  # long, multi-chunk

    chunks = chunk_text(text, chunk_size=200, overlap=50)

    assert len(chunks) > 1
    # Every chunk fits the size budget.
    assert all(len(chunk) <= 200 for chunk in chunks)
    # Coverage: first and last tokens both appear somewhere.
    joined = " ".join(chunks)
    assert "word0" in joined
    assert "word399" in joined
    # Short text returns a single chunk.
    assert chunk_text("just a short line", chunk_size=200) == ["just a short line"]
    assert chunk_text("   ") == []


@pytest.mark.asyncio
async def test_hashing_embedder_is_deterministic_and_lexically_meaningful() -> None:
    embedder = HashingEmbedder(dimensions=256)

    (v1,) = await embedder.embed_texts(["Apple revenue grew on strong iPhone sales"])
    (v1_again,) = await embedder.embed_texts(["Apple revenue grew on strong iPhone sales"])
    (v_related,) = await embedder.embed_texts(["iPhone sales drove Apple revenue growth"])
    (v_unrelated,) = await embedder.embed_texts(["The weather in Norway was cold today"])

    # Deterministic: same text -> identical vector.
    assert v1 == v1_again
    assert len(v1) == 256
    # A passage sharing vocabulary is closer than an unrelated one.
    assert _cosine_similarity(v1, v_related) > _cosine_similarity(v1, v_unrelated)


@pytest.mark.asyncio
async def test_research_service_ingest_and_retrieve_end_to_end() -> None:
    service = ResearchService(
        repository=InMemoryResearchRepository(),
        embedder=HashingEmbedder(dimensions=256),
        chunk_size=200,
        chunk_overlap=40,
    )

    apple = await service.ingest_document(
        IngestDocumentRequest(
            title="Apple FY25 Annual Report",
            content=(
                "Apple reported record revenue driven by strong iPhone demand and "
                "growth in its services segment. Gross margin expanded year over year."
            ),
            document_type="annual_report",
            source="test",
            symbols=("AAPL",),
            sectors=("Technology",),
        )
    )
    await service.ingest_document(
        IngestDocumentRequest(
            title="Reliance Energy Update",
            content=(
                "Reliance discussed expansion of its renewable energy capacity and "
                "new investments in solar power generation across India."
            ),
            document_type="research_report",
            source="test",
            symbols=("RELIANCE.NS",),
            sectors=("Energy",),
        )
    )

    context = await service.search(
        ResearchQueryRequest(query="iPhone revenue and services growth", top_k=3)
    )
    stats = await service.get_stats()
    apple_docs = await service.list_documents(DocumentQueryRequest(symbol="AAPL"))

    assert apple.chunk_count >= 1
    assert context.count >= 1
    # The most relevant passage should come from the Apple document.
    assert context.results[0].document_title == "Apple FY25 Annual Report"
    assert context.results[0].score >= context.results[-1].score  # ranked
    assert stats.total_documents == 2
    assert len(apple_docs.documents) == 1
    assert apple_docs.documents[0].symbols == ("AAPL",)


@pytest.mark.asyncio
async def test_reingesting_same_document_is_idempotent() -> None:
    repo = InMemoryResearchRepository()
    service = ResearchService(
        repository=repo,
        embedder=HashingEmbedder(dimensions=128),
        chunk_size=200,
        chunk_overlap=40,
    )
    request = IngestDocumentRequest(
        title="Earnings Call Q1",
        content="Management guided revenue higher and highlighted margin improvement.",
        document_type="earnings_call",
        source="test",
        symbols=("AAPL",),
    )

    first = await service.ingest_document(request)
    second = await service.ingest_document(request)
    stats = await service.get_stats()

    # Same content -> same document_id -> chunks replaced, not duplicated.
    assert first.document_id == second.document_id
    assert stats.total_documents == 1
    assert stats.total_chunks == first.chunk_count


@pytest.mark.asyncio
async def test_search_without_embedder_returns_empty_context() -> None:
    service = ResearchService(
        repository=InMemoryResearchRepository(),
        embedder=None,
    )

    result = await service.search(ResearchQueryRequest(query="anything"))

    assert result.count == 0
    assert result.results == ()
