from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

from backend.modules.research.domain.entities import (
    DocumentChunk,
    DocumentType,
    Embedding,
    ResearchDocument,
    RetrievedChunk,
)
from backend.modules.research.domain.repositories import ResearchRepository
from backend.modules.research.infrastructure.faiss_index import FaissVectorIndex

logger = logging.getLogger(__name__)

# When a symbol/type filter is active we cannot push it into FAISS (a flat
# index has no metadata predicates), so we over-fetch and filter after. This
# multiplier is the trade-off knob: too low and a filtered query silently
# returns fewer than top_k results, too high and we pay for vectors we discard.
_FILTER_OVERFETCH = 5
_MIN_OVERFETCH = 50


@runtime_checkable
class ChunkSource(Protocol):
    """The one extra capability FAISS needs beyond the repository port.

    Kept as a structural protocol rather than added to ``ResearchRepository``
    so the domain port stays about documents and retrieval, not about how a
    particular index warms itself up.
    """

    async def list_all_chunks(self) -> list[DocumentChunk]: ...


class FaissResearchRepository(ResearchRepository):
    """FAISS-backed retrieval layered over a durable research repository.

    Split of responsibility:
      - the wrapped repository (SQL) stays the source of truth for documents
        and chunks, so nothing is lost on restart;
      - FAISS serves ``search_chunks``, replacing the O(n) Python cosine scan
        with a vectorized index lookup.

    The index is process-local and rebuilt lazily from the durable store on the
    first query after startup. Because the embeddings are L2-normalized before
    indexing, FAISS inner-product scores are cosine similarities — identical
    ranking to the SQL backend, which the test suite asserts directly.

    Every other method delegates, so callers cannot tell the difference and the
    backend is a config switch.
    """

    def __init__(
        self,
        inner: ResearchRepository,
        index: FaissVectorIndex,
    ) -> None:
        self._inner = inner
        self._index = index

    async def save_document(
        self,
        document: ResearchDocument,
        chunks: list[DocumentChunk],
    ) -> None:
        await self._inner.save_document(document, chunks)
        async with self._index.lock:
            # Only touch the index if it is already warm. If it has not been
            # hydrated yet, the next search rebuilds it from SQL and picks
            # these chunks up anyway — indexing them now would double-add.
            if self._index.hydrated:
                self._index.remove_document(document.document_id)
                self._index.add_chunks(chunks)

    async def get_document(
        self,
        document_id: str,
    ) -> ResearchDocument | None:
        return await self._inner.get_document(document_id)

    async def list_documents(
        self,
        symbol: str | None = None,
        document_type: DocumentType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ResearchDocument]:
        return await self._inner.list_documents(
            symbol=symbol,
            document_type=document_type,
            limit=limit,
            offset=offset,
        )

    async def search_chunks(
        self,
        query_embedding: Embedding,
        top_k: int = 5,
        symbol: str | None = None,
        document_type: DocumentType | None = None,
    ) -> list[RetrievedChunk]:
        await self._ensure_hydrated()

        top_k = max(1, int(top_k))
        filtered = symbol is not None or document_type is not None
        wanted = (
            max(top_k * _FILTER_OVERFETCH, _MIN_OVERFETCH) if filtered else top_k
        )

        async with self._index.lock:
            hits = self._index.search(query_embedding, wanted)

        results: list[RetrievedChunk] = []
        for chunk, score in hits:
            if symbol is not None and symbol.upper() not in chunk.symbols:
                continue
            if document_type is not None and chunk.document_type != document_type:
                continue
            results.append(RetrievedChunk(chunk=chunk, score=score))
            if len(results) >= top_k:
                break
        return results

    async def get_stats(
        self,
    ) -> dict[str, int]:
        stats = await self._inner.get_stats()
        return {**stats, "indexed_vectors": self._index.size}

    async def _ensure_hydrated(self) -> None:
        """Rebuild the in-process index from the durable store, once."""

        if self._index.hydrated:
            return
        async with self._index.lock:
            if self._index.hydrated:  # Another request won the race.
                return
            if not isinstance(self._inner, ChunkSource):
                logger.warning(
                    "%s cannot enumerate chunks; the FAISS index will only "
                    "contain documents ingested during this process.",
                    type(self._inner).__name__,
                )
                self._index.mark_hydrated()
                return
            chunks = await self._inner.list_all_chunks()
            indexed = self._index.add_chunks(chunks)
            self._index.mark_hydrated()
            logger.info(
                "FAISS index hydrated: %d/%d chunks indexed (dim=%s).",
                indexed,
                len(chunks),
                self._index.dimensions,
            )


# Purpose:
# Adapter that gives the research knowledge base real vector search while
# keeping SQL as the durable store. Implements the same ResearchRepository
# port, so swapping backends is a configuration change, not a code change.
#
# What Should Not Live Here:
# - Raw FAISS calls (they belong in FaissVectorIndex).
# - Embedding computation.
