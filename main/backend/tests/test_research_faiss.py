from __future__ import annotations

import pytest

from backend.modules.research.application.dto import (
    IngestDocumentRequest,
    ResearchQueryRequest,
)
from backend.modules.research.application.seed_corpus import SEED_CORPUS
from backend.modules.research.application.services import ResearchService
from backend.modules.research.domain.entities import DocumentType
from backend.modules.research.infrastructure.faiss_index import (
    FAISS_AVAILABLE,
    FaissVectorIndex,
)
from backend.modules.research.infrastructure.faiss_repository import (
    FaissResearchRepository,
)
from backend.modules.research.infrastructure.providers import HashingEmbedder
from backend.modules.research.infrastructure.repositories import (
    InMemoryResearchRepository,
)

pytestmark = pytest.mark.skipif(
    not FAISS_AVAILABLE, reason="faiss-cpu is not installed"
)


_CORPUS = [
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
    ),
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
    ),
    IngestDocumentRequest(
        title="Banking Sector Outlook",
        content=(
            "Rising interest rates lifted net interest margins for large private "
            "banks, though credit growth moderated over the quarter."
        ),
        document_type="research_report",
        source="test",
        symbols=("HDFCBANK.NS",),
        sectors=("Financials",),
    ),
]


def _build_services() -> tuple[ResearchService, ResearchService]:
    """A SQL-style service and a FAISS service over identical stores."""

    sql_repo = InMemoryResearchRepository()
    sql_service = ResearchService(
        repository=sql_repo,
        embedder=HashingEmbedder(dimensions=256),
        chunk_size=200,
        chunk_overlap=40,
    )

    faiss_inner = InMemoryResearchRepository()
    faiss_service = ResearchService(
        repository=FaissResearchRepository(faiss_inner, FaissVectorIndex()),
        embedder=HashingEmbedder(dimensions=256),
        chunk_size=200,
        chunk_overlap=40,
    )
    return sql_service, faiss_service


async def _ingest_all(service: ResearchService) -> None:
    for request in _CORPUS:
        await service.ingest_document(request)


@pytest.mark.asyncio
async def test_faiss_and_sql_backends_return_identical_rankings() -> None:
    """The point of the FAISS swap: same answers, different execution.

    Embeddings are L2-normalized before indexing, so FAISS inner-product
    scores are cosine similarities. If this test ever fails, the two backends
    have diverged and retrieval quality is no longer backend-independent.
    """
    sql_service, faiss_service = _build_services()
    await _ingest_all(sql_service)
    await _ingest_all(faiss_service)

    for query in (
        "iPhone revenue and services growth",
        "solar and renewable capacity investment",
        "net interest margin and credit growth",
    ):
        request = ResearchQueryRequest(query=query, top_k=3)
        sql_context = await sql_service.search(request)
        faiss_context = await faiss_service.search(request)

        sql_titles = [r.document_title for r in sql_context.results]
        faiss_titles = [r.document_title for r in faiss_context.results]
        assert faiss_titles == sql_titles, f"ranking diverged for query: {query}"

        for sql_result, faiss_result in zip(sql_context.results, faiss_context.results):
            assert faiss_result.score == pytest.approx(sql_result.score, abs=1e-5)


@pytest.mark.asyncio
async def test_faiss_respects_symbol_and_type_filters() -> None:
    _, faiss_service = _build_services()
    await _ingest_all(faiss_service)

    by_symbol = await faiss_service.search(
        ResearchQueryRequest(query="growth", top_k=5, symbol="AAPL")
    )
    by_type = await faiss_service.search(
        ResearchQueryRequest(query="growth", top_k=5, document_type="research_report")
    )

    assert by_symbol.count >= 1
    assert all("AAPL" in r.symbols for r in by_symbol.results)
    assert by_type.count >= 1
    assert all(
        r.document_type == DocumentType.RESEARCH_REPORT.value for r in by_type.results
    )


@pytest.mark.asyncio
async def test_reingest_replaces_vectors_instead_of_duplicating() -> None:
    index = FaissVectorIndex()
    repo = FaissResearchRepository(InMemoryResearchRepository(), index)
    service = ResearchService(
        repository=repo,
        embedder=HashingEmbedder(dimensions=128),
        chunk_size=200,
        chunk_overlap=40,
    )

    first = await service.ingest_document(_CORPUS[0])
    # Warm the index, then re-ingest the same document.
    await service.search(ResearchQueryRequest(query="iPhone", top_k=3))
    second = await service.ingest_document(_CORPUS[0])

    stats = await service.get_stats()

    assert first.document_id == second.document_id
    assert index.size == first.chunk_count  # replaced, not appended
    assert stats.total_chunks == first.chunk_count


@pytest.mark.asyncio
async def test_index_hydrates_from_the_durable_store_on_first_query() -> None:
    """Simulates a restart: chunks already in SQL, index cold."""

    inner = InMemoryResearchRepository()
    warm_service = ResearchService(
        repository=inner,
        embedder=HashingEmbedder(dimensions=256),
        chunk_size=200,
        chunk_overlap=40,
    )
    await _ingest_all(warm_service)  # data lands in the store, no index involved

    index = FaissVectorIndex()
    assert index.size == 0

    cold_service = ResearchService(
        repository=FaissResearchRepository(inner, index),
        embedder=HashingEmbedder(dimensions=256),
        chunk_size=200,
        chunk_overlap=40,
    )
    context = await cold_service.search(
        ResearchQueryRequest(query="iPhone revenue and services growth", top_k=3)
    )

    assert index.size > 0  # hydrated lazily from the store
    assert context.count >= 1
    assert context.results[0].document_title == "Apple FY25 Annual Report"


@pytest.mark.asyncio
async def test_seed_corpus_ingests_and_answers_realistic_queries() -> None:
    """The shipped knowledge base must actually retrieve, not just exist.

    Runs the real corpus through the real pipeline (chunk -> embed -> FAISS ->
    retrieve) so a broken or empty passage fails here rather than in a demo.
    Queries are matched on topic, not exact wording, since the default embedder
    is lexical.
    """
    index = FaissVectorIndex()
    service = ResearchService(
        repository=FaissResearchRepository(InMemoryResearchRepository(), index),
        embedder=HashingEmbedder(dimensions=512),
    )

    total_chunks = 0
    for request in SEED_CORPUS:
        result = await service.ingest_document(request)
        assert result.chunk_count >= 1, f"{request.title} produced no chunks"
        total_chunks += result.chunk_count

    stats = await service.get_stats()
    assert stats.total_documents == len(SEED_CORPUS)
    assert stats.total_chunks == total_chunks

    # Each query should surface the document that actually covers the topic.
    expectations = {
        "drawdown recovery percentage gain needed to break even": (
            "The Mathematics of Drawdown Recovery"
        ),
        "efficient frontier mean variance optimization sharpe": (
            "Modern Portfolio Theory and the Efficient Frontier"
        ),
        "pandemic lockdown crash and central bank response": (
            "COVID-19 Crash of 2020: Speed of Decline and Policy Response"
        ),
        "oil price shock hurting airlines and helping energy producers": (
            "Oil Supply Shocks and Sector Rotation"
        ),
    }
    for query, expected_title in expectations.items():
        context = await service.search(ResearchQueryRequest(query=query, top_k=3))
        titles = [r.document_title for r in context.results]
        assert expected_title in titles, f"{query!r} did not retrieve {expected_title!r}"

    # The first search hydrated the index from the store; every chunk is in it.
    assert index.size == total_chunks


@pytest.mark.asyncio
async def test_empty_index_returns_no_results_instead_of_failing() -> None:
    service = ResearchService(
        repository=FaissResearchRepository(
            InMemoryResearchRepository(), FaissVectorIndex()
        ),
        embedder=HashingEmbedder(dimensions=64),
    )

    context = await service.search(ResearchQueryRequest(query="anything", top_k=5))

    assert context.count == 0
