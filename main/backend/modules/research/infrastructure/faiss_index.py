from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable, Sequence

import numpy as np

from backend.modules.research.domain.entities import DocumentChunk, Embedding

logger = logging.getLogger(__name__)

try:  # pragma: no cover - exercised by the import-failure path in wiring
    import faiss

    FAISS_AVAILABLE = True
except ImportError:  # pragma: no cover
    faiss = None  # type: ignore[assignment]
    FAISS_AVAILABLE = False


def _to_matrix(vectors: Sequence[Embedding]) -> np.ndarray:
    """Stack embeddings into the float32, L2-normalized matrix FAISS wants.

    Normalizing here is what makes an inner-product index equivalent to cosine
    similarity: for unit vectors, ``a . b == cos(a, b)``. That equivalence is
    the whole reason the FAISS backend returns the same ranking as the SQL
    backend's explicit cosine — see ``test_research_faiss.py``.
    """

    matrix = np.asarray(vectors, dtype=np.float32)
    if matrix.ndim == 1:
        matrix = matrix.reshape(1, -1)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    # Guard the zero vector: leave it at zero rather than dividing by zero, so
    # it simply never wins a search instead of producing NaNs that poison one.
    norms[norms == 0.0] = 1.0
    return matrix / norms


class FaissVectorIndex:
    """Process-local FAISS index over research chunk embeddings.

    Uses ``IndexFlatIP`` (exact inner-product search) wrapped in an
    ``IndexIDMap2`` so chunks keep stable integer ids that survive deletion.
    Flat is exact, not approximate — at this corpus size an approximate index
    (IVF/HNSW) would cost recall for a speedup nobody can measure. The seam to
    upgrade is one line in ``_new_index``.

    Alongside the vectors it keeps a docstore: ``chunk_id -> DocumentChunk``.
    FAISS only stores vectors and ids, so retrieving the actual passage needs a
    payload map (this is the same shape as LangChain's FAISS + docstore
    pairing). It means the index is memory-resident; the SQL store remains the
    durable source of truth and the index is rebuilt from it on startup.

    Thread/task safety: all mutating calls are guarded by an ``asyncio.Lock``
    held by the owning repository, since one index instance is shared across
    requests.
    """

    def __init__(self) -> None:
        self._index = None
        self._dimensions: int | None = None
        self._docstore: dict[str, DocumentChunk] = {}
        self._id_to_chunk_id: dict[int, str] = {}
        self._chunk_id_to_id: dict[str, int] = {}
        self._document_chunk_ids: dict[str, set[str]] = {}
        self._next_id = 0
        self._hydrated = False
        self.lock = asyncio.Lock()

    @property
    def available(self) -> bool:
        return FAISS_AVAILABLE

    @property
    def hydrated(self) -> bool:
        """True once the index has been loaded from the durable store."""
        return self._hydrated

    def mark_hydrated(self) -> None:
        self._hydrated = True

    @property
    def size(self) -> int:
        return 0 if self._index is None else int(self._index.ntotal)

    @property
    def dimensions(self) -> int | None:
        return self._dimensions

    def reset(self) -> None:
        self._index = None
        self._dimensions = None
        self._docstore.clear()
        self._id_to_chunk_id.clear()
        self._chunk_id_to_id.clear()
        self._document_chunk_ids.clear()
        self._next_id = 0
        self._hydrated = False

    def _new_index(self, dimensions: int):
        # IndexFlatIP = exact inner product. IndexIDMap2 lets us attach our own
        # int64 ids and supports remove_ids, which plain IndexFlat does not.
        return faiss.IndexIDMap2(faiss.IndexFlatIP(dimensions))

    def add_chunks(self, chunks: Iterable[DocumentChunk]) -> int:
        """Add chunks to the index, replacing any with the same chunk id.

        Returns the number actually indexed. Chunks whose embedding width does
        not match the index are skipped with a warning rather than raising:
        that mismatch means they were embedded by a different model, and the
        existing SQL backend already treats those as non-comparable (score 0).
        """

        chunks = [chunk for chunk in chunks if chunk.embedding]
        if not chunks:
            return 0

        if self._index is None:
            self._dimensions = len(chunks[0].embedding)
            self._index = self._new_index(self._dimensions)

        usable: list[DocumentChunk] = []
        for chunk in chunks:
            if len(chunk.embedding) != self._dimensions:
                logger.warning(
                    "Skipping chunk %s: embedding width %d does not match the "
                    "index width %d (re-ingest after switching embedders).",
                    chunk.chunk_id,
                    len(chunk.embedding),
                    self._dimensions,
                )
                continue
            usable.append(chunk)

        if not usable:
            return 0

        # Re-adding a chunk id must not leave a stale vector behind.
        self._remove_chunk_ids([c.chunk_id for c in usable if c.chunk_id in self._chunk_id_to_id])

        ids = []
        for chunk in usable:
            numeric_id = self._next_id
            self._next_id += 1
            ids.append(numeric_id)
            self._id_to_chunk_id[numeric_id] = chunk.chunk_id
            self._chunk_id_to_id[chunk.chunk_id] = numeric_id
            self._docstore[chunk.chunk_id] = chunk
            self._document_chunk_ids.setdefault(chunk.document_id, set()).add(
                chunk.chunk_id
            )

        self._index.add_with_ids(
            _to_matrix([chunk.embedding for chunk in usable]),
            np.asarray(ids, dtype=np.int64),
        )
        return len(usable)

    def remove_document(self, document_id: str) -> int:
        """Drop every chunk belonging to a document. Returns how many went."""

        chunk_ids = self._document_chunk_ids.pop(document_id, set())
        if not chunk_ids:
            return 0
        removed = self._remove_chunk_ids(list(chunk_ids))
        return removed

    def _remove_chunk_ids(self, chunk_ids: Sequence[str]) -> int:
        if not chunk_ids or self._index is None:
            return 0
        numeric_ids = [
            self._chunk_id_to_id[chunk_id]
            for chunk_id in chunk_ids
            if chunk_id in self._chunk_id_to_id
        ]
        if not numeric_ids:
            return 0

        selector = faiss.IDSelectorBatch(np.asarray(numeric_ids, dtype=np.int64))
        self._index.remove_ids(selector)

        for chunk_id in chunk_ids:
            numeric_id = self._chunk_id_to_id.pop(chunk_id, None)
            if numeric_id is not None:
                self._id_to_chunk_id.pop(numeric_id, None)
            chunk = self._docstore.pop(chunk_id, None)
            if chunk is not None:
                siblings = self._document_chunk_ids.get(chunk.document_id)
                if siblings is not None:
                    siblings.discard(chunk_id)
                    if not siblings:
                        self._document_chunk_ids.pop(chunk.document_id, None)
        return len(numeric_ids)

    def search(
        self,
        query_embedding: Embedding,
        top_k: int,
    ) -> list[tuple[DocumentChunk, float]]:
        """Return the ``top_k`` nearest chunks as ``(chunk, cosine score)``."""

        if self._index is None or self._index.ntotal == 0 or not query_embedding:
            return []
        if self._dimensions is not None and len(query_embedding) != self._dimensions:
            # Query embedded by a different model than the corpus — the SQL
            # backend scores these 0, so returning nothing is the same answer.
            logger.warning(
                "Query embedding width %d does not match index width %d; "
                "returning no matches.",
                len(query_embedding),
                self._dimensions,
            )
            return []

        wanted = max(1, min(int(top_k), int(self._index.ntotal)))
        scores, ids = self._index.search(_to_matrix([query_embedding]), wanted)

        results: list[tuple[DocumentChunk, float]] = []
        for numeric_id, score in zip(ids[0], scores[0]):
            if numeric_id == -1:  # FAISS pads short result sets with -1.
                continue
            chunk_id = self._id_to_chunk_id.get(int(numeric_id))
            if chunk_id is None:
                continue
            chunk = self._docstore.get(chunk_id)
            if chunk is None:
                continue
            results.append((chunk, float(score)))
        return results


# Purpose:
# The FAISS vector-search primitive for the research knowledge base: an exact
# inner-product index over L2-normalized embeddings (so scores are cosine),
# plus the chunk docstore needed to turn hits back into citable passages.
#
# What Should Not Live Here:
# - SQL / persistence (the repository decorator owns durability).
# - Embedding computation (that is an embedder adapter).
# - Filtering by symbol or document type (the repository post-filters).
