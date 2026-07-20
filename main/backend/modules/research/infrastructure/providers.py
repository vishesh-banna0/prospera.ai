from __future__ import annotations

import hashlib
import math
import re

from backend.modules.research.application.providers import (
    DocumentParserContract,
    EmbeddingProviderContract,
)
from backend.modules.research.domain.entities import Embedding

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


class HashingEmbedder(EmbeddingProviderContract):
    """Deterministic feature-hashing text embedder.

    The Phase 9 default: no model download, no network, fully reproducible,
    and exercised in the test suite. It maps each token to a bucket via a
    stable hash (with sign hashing to limit collisions), accumulates a vector,
    and L2-normalizes it so a dot product equals cosine similarity.

    This is a genuine lexical baseline — two passages that share vocabulary
    land near each other — which is enough to prove the ingest/retrieve
    pipeline end-to-end. Swap in a sentence-transformers or hosted-API adapter
    (same contract) for semantic (meaning-based) retrieval later.

    Because ingestion and querying both go through this class, their vectors
    are always comparable.
    """

    name = "hashing-v1"

    def __init__(self, dimensions: int = 512) -> None:
        if dimensions <= 0:
            raise ValueError("Embedding dimensions must be positive.")
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed_texts(
        self,
        texts: list[str],
    ) -> list[Embedding]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(
        self,
        text: str,
    ) -> Embedding:
        vector = [0.0] * self._dimensions
        for token in _TOKEN_PATTERN.findall(text.lower()):
            digest = hashlib.md5(token.encode("utf-8")).digest()
            bucket_hash = int.from_bytes(digest[:8], "big")
            index = bucket_hash % self._dimensions
            sign = 1.0 if (bucket_hash >> 63) & 1 == 0 else -1.0
            vector[index] += sign
        return self._normalize(vector)

    def _normalize(
        self,
        vector: list[float],
    ) -> Embedding:
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0.0:
            return tuple(vector)
        return tuple(value / norm for value in vector)


class PlainTextParser(DocumentParserContract):
    """Default document parser: treats input as already-extracted plain text.

    PDF/HTML/DOCX extraction is intentionally out of scope for the Phase 9 thin
    slice (financial PDFs with tables are their own project). Add a parser
    adapter implementing ``DocumentParserContract`` when binary formats are
    needed; the ingestion pipeline will not change.
    """

    def parse(
        self,
        content: str,
        content_type: str = "text/plain",
    ) -> str:
        return content or ""
