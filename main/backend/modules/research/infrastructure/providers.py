from __future__ import annotations

import hashlib
import logging
import math
import re

from backend.modules.research.application.providers import (
    DocumentParserContract,
    EmbeddingProviderContract,
)
from backend.modules.research.domain.entities import Embedding
from backend.shared.llm import LLMClient

logger = logging.getLogger(__name__)

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


class LLMEmbedder(EmbeddingProviderContract):
    """Semantic embedder backed by an OpenAI-compatible ``/embeddings`` endpoint.

    This is the Tier-5 upgrade over ``HashingEmbedder``: instead of a lexical
    bag-of-words vector, it produces true semantic embeddings from a hosted /
    local model (e.g. Ollama's ``nomic-embed-text``), so passages that mean the
    same thing land near each other even without shared vocabulary.

    Robustness mirrors the rest of the LLM adapters: if the embeddings endpoint
    is unreachable or errors, it falls back to the injected deterministic
    embedder so retrieval never hard-fails.

    Caveat — vectors from different models are not comparable. Ingestion and
    querying must use the same embedder; if some chunks were embedded while the
    LLM was down (hashing fallback) and others while it was up (LLM), the
    mismatched-dimension pairs simply score 0 (see ``_cosine_similarity``) and
    are skipped rather than returning wrong results. Re-ingest after switching
    embedders for full recall.
    """

    name = "llm"

    def __init__(
        self,
        llm: LLMClient,
        model: str,
        fallback: EmbeddingProviderContract | None = None,
        expected_dimensions: int = 768,
    ) -> None:
        self._llm = llm
        self._model = model
        self._fallback = fallback
        # Best-effort until the first successful call reports the real width.
        # (Nothing outside the contract actually reads this today.)
        self._dimensions = expected_dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed_texts(
        self,
        texts: list[str],
    ) -> list[Embedding]:
        if not texts:
            return []
        try:
            raw_vectors = await self._llm.embed(texts, self._model)
            vectors = [tuple(float(x) for x in vector) for vector in raw_vectors]
            if any(len(vector) == 0 for vector in vectors):
                raise ValueError("LLM returned an empty embedding vector.")
            self._dimensions = len(vectors[0])
            return vectors
        except Exception as exc:
            if self._fallback is None:
                raise
            logger.warning(
                "LLM embedding failed (%s); using the %s fallback embedder.",
                exc,
                self._fallback.name,
            )
            return await self._fallback.embed_texts(texts)


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
