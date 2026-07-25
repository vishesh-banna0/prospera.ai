from __future__ import annotations

import pytest

from backend.modules.research.application.dto import (
    DocumentQueryRequest,
    IngestDocumentRequest,
    ResearchQueryRequest,
)
from backend.modules.research.application.services import ResearchService
from backend.modules.research.domain.chunking import chunk_text
from backend.modules.research.infrastructure.providers import (
    HashingEmbedder,
    LLMEmbedder,
)
from backend.modules.research.infrastructure.repositories import (
    InMemoryResearchRepository,
    _cosine_similarity,
)
from backend.shared.llm import LLMClient


class _FakeEmbedLLM(LLMClient):
    """Fake LLM exposing an ``embed`` method (or raising) for offline tests."""

    def __init__(self, dim: int = 8, error: Exception | None = None) -> None:
        self._dim = dim
        self._error = error

    async def complete(self, system, user, temperature=0.0, max_tokens=None) -> str:
        return ""

    async def embed(self, inputs: list[str], model: str) -> list[list[float]]:
        if self._error is not None:
            raise self._error
        return [[float((len(text) + i) % 7) for i in range(self._dim)] for text in inputs]


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
async def test_llm_embedder_uses_llm_and_reports_dimensions() -> None:
    embedder = LLMEmbedder(
        _FakeEmbedLLM(dim=8), model="fake-embed", fallback=HashingEmbedder()
    )

    vectors = await embedder.embed_texts(["alpha", "beta gamma"])

    assert len(vectors) == 2
    assert all(len(v) == 8 for v in vectors)
    assert embedder.dimensions == 8  # learned from the first successful call
    assert await embedder.embed_texts([]) == []


@pytest.mark.asyncio
async def test_llm_embedder_falls_back_on_error() -> None:
    fallback = HashingEmbedder(dimensions=32)
    embedder = LLMEmbedder(
        _FakeEmbedLLM(error=RuntimeError("no embeddings endpoint")),
        model="fake-embed",
        fallback=fallback,
    )

    vectors = await embedder.embed_texts(["some financial text"])

    assert len(vectors) == 1
    # Fell back to the hashing embedder's vector width.
    assert len(vectors[0]) == 32


@pytest.mark.asyncio
async def test_llm_embedder_raises_without_fallback_on_error() -> None:
    embedder = LLMEmbedder(
        _FakeEmbedLLM(error=RuntimeError("boom")),
        model="fake-embed",
        fallback=None,
    )
    with pytest.raises(RuntimeError):
        await embedder.embed_texts(["x"])


@pytest.mark.asyncio
async def test_search_without_embedder_returns_empty_context() -> None:
    service = ResearchService(
        repository=InMemoryResearchRepository(),
        embedder=None,
    )

    result = await service.search(ResearchQueryRequest(query="anything"))

    assert result.count == 0
    assert result.results == ()
