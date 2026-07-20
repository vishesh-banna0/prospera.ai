from __future__ import annotations

import hashlib
import re
from collections.abc import Awaitable
from collections.abc import Callable
from datetime import UTC
from datetime import datetime

from backend.modules.research.application.dto import (
    DocumentQueryRequest,
    DocumentView,
    DocumentsView,
    IngestDocumentRequest,
    IngestDocumentView,
    ResearchContextView,
    ResearchQueryRequest,
    ResearchStatsView,
    RetrievedChunkView,
)
from backend.modules.research.application.providers import (
    DocumentParserContract,
    EmbeddingProviderContract,
)
from backend.modules.research.domain.chunking import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    chunk_text,
)
from backend.modules.research.domain.entities import (
    DocumentChunk,
    DocumentType,
    ResearchDocument,
    RetrievedChunk,
)
from backend.modules.research.domain.repositories import ResearchRepository


class ResearchService:
    """Phase 9 application boundary for the research knowledge base.

    Ingestion pipeline: ``parse -> chunk -> embed -> store``.
    Retrieval: ``embed query -> similarity search -> ranked context``.

    The embedder and parser are injected as ports so the strategy is
    swappable; the store is a repository port so persistence/vector-search is
    swappable (in-memory for tests, SQL by default, Qdrant later).
    """

    def __init__(
        self,
        repository: ResearchRepository,
        embedder: EmbeddingProviderContract | None = None,
        parser: DocumentParserContract | None = None,
        commit: Callable[[], Awaitable[None]] | None = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> None:
        self._repository = repository
        self._embedder = embedder
        self._parser = parser
        self._commit = commit
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    async def ingest_document(
        self,
        request: IngestDocumentRequest,
    ) -> IngestDocumentView:
        if self._embedder is None:
            return IngestDocumentView(
                document_id="",
                title=request.title,
                chunk_count=0,
                message="No embedding provider is configured.",
            )

        raw_text = request.content
        if self._parser is not None:
            raw_text = self._parser.parse(raw_text)
        text = self._collapse_whitespace(raw_text)
        if not text:
            raise ValueError("Document content is empty after parsing.")

        title = self._collapse_whitespace(request.title)
        source = self._collapse_whitespace(request.source) or "manual"
        document_type = self._coerce_document_type(request.document_type)
        symbols = self._normalize_symbols(request.symbols)
        sectors = self._normalize_sectors(request.sectors)
        content_hash = self._content_hash(text)
        document_id = self._document_id(title, source, content_hash)

        chunk_texts = chunk_text(text, self._chunk_size, self._chunk_overlap)
        embeddings = await self._embedder.embed_texts(chunk_texts)

        document = ResearchDocument(
            document_id=document_id,
            title=title,
            document_type=document_type,
            source=source,
            symbols=symbols,
            sectors=sectors,
            published_at=self._normalize_datetime(request.published_at),
            content_hash=content_hash,
            chunk_count=len(chunk_texts),
        )

        chunks = [
            DocumentChunk(
                chunk_id=f"{document_id}:{index}",
                document_id=document_id,
                chunk_index=index,
                text=chunk_body,
                embedding=embedding,
                document_type=document_type,
                document_title=title,
                symbols=symbols,
                sectors=sectors,
            )
            for index, (chunk_body, embedding) in enumerate(zip(chunk_texts, embeddings))
        ]

        await self._repository.save_document(document, chunks)
        if self._commit is not None:
            await self._commit()

        return IngestDocumentView(
            document_id=document_id,
            title=title,
            chunk_count=len(chunks),
        )

    async def search(
        self,
        request: ResearchQueryRequest,
    ) -> ResearchContextView:
        query = self._collapse_whitespace(request.query)
        if not query:
            raise ValueError("Research query cannot be blank.")
        if self._embedder is None:
            return ResearchContextView(query=query, results=(), count=0)

        query_embedding = (await self._embedder.embed_texts([query]))[0]
        results = await self._repository.search_chunks(
            query_embedding=query_embedding,
            top_k=self._normalize_top_k(request.top_k),
            symbol=self._optional_upper(request.symbol),
            document_type=self._optional_document_type(request.document_type),
        )

        return ResearchContextView(
            query=query,
            results=tuple(self._to_chunk_view(result) for result in results),
            count=len(results),
        )

    async def list_documents(
        self,
        request: DocumentQueryRequest,
    ) -> DocumentsView:
        limit = self._normalize_limit(request.limit)
        offset = max(0, request.offset)
        documents = await self._repository.list_documents(
            symbol=self._optional_upper(request.symbol),
            document_type=self._optional_document_type(request.document_type),
            limit=limit,
            offset=offset,
        )
        return DocumentsView(
            documents=tuple(self._to_document_view(document) for document in documents),
            count=len(documents),
            limit=limit,
            offset=offset,
        )

    async def get_document(
        self,
        document_id: str,
    ) -> DocumentView:
        document = await self._repository.get_document(document_id)
        if document is None:
            raise ValueError(f"Research document '{document_id}' was not found.")
        return self._to_document_view(document)

    async def get_stats(
        self,
    ) -> ResearchStatsView:
        stats = await self._repository.get_stats()
        return ResearchStatsView(
            total_documents=stats.get("documents", 0),
            total_chunks=stats.get("chunks", 0),
        )

    def _coerce_document_type(
        self,
        raw_document_type: str | None,
    ) -> DocumentType:
        if raw_document_type is None or not str(raw_document_type).strip():
            return DocumentType.OTHER
        try:
            return DocumentType(str(raw_document_type).strip().lower())
        except ValueError:
            return DocumentType.OTHER

    def _optional_document_type(
        self,
        raw_document_type: str | None,
    ) -> DocumentType | None:
        if raw_document_type is None or not str(raw_document_type).strip():
            return None
        try:
            return DocumentType(str(raw_document_type).strip().lower())
        except ValueError:
            return None

    def _normalize_symbols(
        self,
        symbols: tuple[str, ...],
    ) -> tuple[str, ...]:
        values = {self._collapse_whitespace(symbol).upper() for symbol in symbols}
        values.discard("")
        return tuple(sorted(values))

    def _normalize_sectors(
        self,
        sectors: tuple[str, ...],
    ) -> tuple[str, ...]:
        values = {self._collapse_whitespace(sector).title() for sector in sectors}
        values.discard("")
        return tuple(sorted(values))

    def _normalize_top_k(
        self,
        top_k: int,
    ) -> int:
        return min(max(1, int(top_k)), 50)

    def _normalize_limit(
        self,
        limit: int,
    ) -> int:
        return min(max(1, int(limit)), 200)

    def _normalize_datetime(
        self,
        value: datetime | None,
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

    def _optional_upper(
        self,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None
        clean = self._collapse_whitespace(value)
        return clean.upper() if clean else None

    def _collapse_whitespace(
        self,
        value: str,
    ) -> str:
        return re.sub(r"\s+", " ", value).strip()

    def _content_hash(
        self,
        text: str,
    ) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _document_id(
        self,
        title: str,
        source: str,
        content_hash: str,
    ) -> str:
        fingerprint = "|".join((title.lower(), source.lower(), content_hash))
        return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()

    def _to_chunk_view(
        self,
        result: RetrievedChunk,
    ) -> RetrievedChunkView:
        chunk = result.chunk
        return RetrievedChunkView(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            document_title=chunk.document_title,
            document_type=chunk.document_type.value,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            score=round(float(result.score), 6),
            symbols=chunk.symbols,
            sectors=chunk.sectors,
        )

    def _to_document_view(
        self,
        document: ResearchDocument,
    ) -> DocumentView:
        return DocumentView(
            document_id=document.document_id,
            title=document.title,
            document_type=document.document_type.value,
            source=document.source,
            symbols=document.symbols,
            sectors=document.sectors,
            published_at=document.published_at,
            chunk_count=document.chunk_count,
            created_at=document.created_at,
        )
