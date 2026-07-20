from __future__ import annotations

import math
from datetime import UTC
from datetime import datetime

from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.modules.research.domain.entities import (
    DocumentChunk,
    DocumentType,
    Embedding,
    ResearchDocument,
    RetrievedChunk,
)
from backend.modules.research.domain.repositories import ResearchRepository
from backend.modules.research.infrastructure.models import (
    DocumentChunkModel,
    ResearchDocumentModel,
)


def _cosine_similarity(
    left: Embedding,
    right: Embedding,
) -> float:
    """Cosine similarity, robust to non-normalized vectors."""
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = 0.0
    left_norm = 0.0
    right_norm = 0.0
    for a, b in zip(left, right):
        dot += a * b
        left_norm += a * a
        right_norm += b * b
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (math.sqrt(left_norm) * math.sqrt(right_norm))


class InMemoryResearchRepository(ResearchRepository):
    """Dict-backed research store for tests and offline development."""

    def __init__(self) -> None:
        self._documents: dict[str, ResearchDocument] = {}
        self._chunks: dict[str, DocumentChunk] = {}

    async def save_document(
        self,
        document: ResearchDocument,
        chunks: list[DocumentChunk],
    ) -> None:
        self._documents[document.document_id] = document
        # Replace this document's chunks so re-ingest is idempotent.
        self._chunks = {
            chunk_id: chunk
            for chunk_id, chunk in self._chunks.items()
            if chunk.document_id != document.document_id
        }
        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk

    async def get_document(
        self,
        document_id: str,
    ) -> ResearchDocument | None:
        return self._documents.get(document_id)

    async def list_documents(
        self,
        symbol: str | None = None,
        document_type: DocumentType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ResearchDocument]:
        documents = sorted(
            self._documents.values(),
            key=lambda document: document.created_at,
            reverse=True,
        )
        filtered = [
            document
            for document in documents
            if self._document_matches(document, symbol, document_type)
        ]
        return filtered[offset : offset + limit]

    async def search_chunks(
        self,
        query_embedding: Embedding,
        top_k: int = 5,
        symbol: str | None = None,
        document_type: DocumentType | None = None,
    ) -> list[RetrievedChunk]:
        candidates = [
            chunk
            for chunk in self._chunks.values()
            if self._chunk_matches(chunk, symbol, document_type)
        ]
        scored = [
            RetrievedChunk(
                chunk=chunk,
                score=_cosine_similarity(query_embedding, chunk.embedding),
            )
            for chunk in candidates
        ]
        scored.sort(key=lambda result: result.score, reverse=True)
        return scored[:top_k]

    async def get_stats(
        self,
    ) -> dict[str, int]:
        return {
            "documents": len(self._documents),
            "chunks": len(self._chunks),
        }

    def _document_matches(
        self,
        document: ResearchDocument,
        symbol: str | None,
        document_type: DocumentType | None,
    ) -> bool:
        if symbol is not None and symbol.upper() not in document.symbols:
            return False
        if document_type is not None and document.document_type != document_type:
            return False
        return True

    def _chunk_matches(
        self,
        chunk: DocumentChunk,
        symbol: str | None,
        document_type: DocumentType | None,
    ) -> bool:
        if symbol is not None and symbol.upper() not in chunk.symbols:
            return False
        if document_type is not None and chunk.document_type != document_type:
            return False
        return True


class SqlResearchRepository(ResearchRepository):
    """SQLAlchemy-backed research store.

    Vectors are stored as JSON and similarity is computed in Python. This is
    the honest thin-slice scaling story: correct and simple, but O(n) per
    query. A Postgres+pgvector or Qdrant adapter implementing the same
    contract is the path to scale — no caller changes required.
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def save_document(
        self,
        document: ResearchDocument,
        chunks: list[DocumentChunk],
    ) -> None:
        stmt = select(ResearchDocumentModel).where(
            ResearchDocumentModel.document_id == document.document_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            self._session.add(self._document_to_model(document))
        else:
            self._update_document_model(model, document)
            # Replace existing chunks so re-ingest is idempotent.
            await self._session.execute(
                delete(DocumentChunkModel).where(
                    DocumentChunkModel.document_id == document.document_id
                )
            )

        for chunk in chunks:
            self._session.add(self._chunk_to_model(chunk))

        await self._session.flush()

    async def get_document(
        self,
        document_id: str,
    ) -> ResearchDocument | None:
        stmt = select(ResearchDocumentModel).where(
            ResearchDocumentModel.document_id == document_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._model_to_document(model)

    async def list_documents(
        self,
        symbol: str | None = None,
        document_type: DocumentType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ResearchDocument]:
        stmt = select(ResearchDocumentModel)
        if document_type is not None:
            stmt = stmt.where(ResearchDocumentModel.document_type == document_type.value)
        stmt = stmt.order_by(ResearchDocumentModel.created_at.desc())
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        documents = [self._model_to_document(model) for model in models]
        if symbol is not None:
            documents = [
                document for document in documents if symbol.upper() in document.symbols
            ]
        return documents[offset : offset + limit]

    async def search_chunks(
        self,
        query_embedding: Embedding,
        top_k: int = 5,
        symbol: str | None = None,
        document_type: DocumentType | None = None,
    ) -> list[RetrievedChunk]:
        stmt = select(DocumentChunkModel)
        if document_type is not None:
            stmt = stmt.where(DocumentChunkModel.document_type == document_type.value)
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        scored: list[RetrievedChunk] = []
        for model in models:
            chunk = self._model_to_chunk(model)
            if symbol is not None and symbol.upper() not in chunk.symbols:
                continue
            scored.append(
                RetrievedChunk(
                    chunk=chunk,
                    score=_cosine_similarity(query_embedding, chunk.embedding),
                )
            )
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]

    async def get_stats(
        self,
    ) -> dict[str, int]:
        documents_result = await self._session.execute(
            select(func.count()).select_from(ResearchDocumentModel)
        )
        chunks_result = await self._session.execute(
            select(func.count()).select_from(DocumentChunkModel)
        )
        return {
            "documents": int(documents_result.scalar_one() or 0),
            "chunks": int(chunks_result.scalar_one() or 0),
        }

    def _document_to_model(
        self,
        document: ResearchDocument,
    ) -> ResearchDocumentModel:
        return ResearchDocumentModel(
            document_id=document.document_id,
            title=document.title,
            document_type=document.document_type.value,
            source=document.source,
            symbols=list(document.symbols),
            sectors=list(document.sectors),
            content_hash=document.content_hash,
            chunk_count=document.chunk_count,
            published_at=document.published_at,
            created_at=document.created_at,
        )

    def _update_document_model(
        self,
        model: ResearchDocumentModel,
        document: ResearchDocument,
    ) -> None:
        model.title = document.title
        model.document_type = document.document_type.value
        model.source = document.source
        model.symbols = list(document.symbols)
        model.sectors = list(document.sectors)
        model.content_hash = document.content_hash
        model.chunk_count = document.chunk_count
        model.published_at = document.published_at
        model.created_at = document.created_at

    def _chunk_to_model(
        self,
        chunk: DocumentChunk,
    ) -> DocumentChunkModel:
        return DocumentChunkModel(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            embedding=list(chunk.embedding),
            document_type=chunk.document_type.value,
            document_title=chunk.document_title,
            symbols=list(chunk.symbols),
            sectors=list(chunk.sectors),
            created_at=chunk.created_at,
        )

    def _model_to_document(
        self,
        model: ResearchDocumentModel,
    ) -> ResearchDocument:
        return ResearchDocument(
            document_id=model.document_id,
            title=model.title,
            document_type=DocumentType(model.document_type),
            source=model.source,
            symbols=tuple(model.symbols or ()),
            sectors=tuple(model.sectors or ()),
            published_at=self._ensure_aware(model.published_at),
            content_hash=model.content_hash,
            chunk_count=model.chunk_count,
            created_at=self._ensure_aware(model.created_at),
        )

    def _model_to_chunk(
        self,
        model: DocumentChunkModel,
    ) -> DocumentChunk:
        return DocumentChunk(
            chunk_id=model.chunk_id,
            document_id=model.document_id,
            chunk_index=model.chunk_index,
            text=model.text,
            embedding=tuple(model.embedding or ()),
            document_type=DocumentType(model.document_type),
            document_title=model.document_title,
            symbols=tuple(model.symbols or ()),
            sectors=tuple(model.sectors or ()),
            created_at=self._ensure_aware(model.created_at),
        )

    def _ensure_aware(
        self,
        value: datetime | None,
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
