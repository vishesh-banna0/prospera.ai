from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from backend.modules.research.domain.entities import Embedding


class EmbeddingProviderContract(ABC):
    """Port for turning text into dense vectors.

    This is the seam that keeps the embedding *model* swappable. The Phase 9
    default is a deterministic feature-hashing embedder (no model download, no
    network, reproducible in tests). A production adapter can wrap
    sentence-transformers or a hosted embedding API behind this same contract
    without changing the service, the store, or the API.

    The same embedder MUST be used for both ingestion and querying — vectors
    from different models are not comparable.
    """

    @property
    @abstractmethod
    def dimensions(self) -> int:
        raise NotImplementedError

    @abstractmethod
    async def embed_texts(
        self,
        texts: list[str],
    ) -> list[Embedding]:
        raise NotImplementedError


class DocumentParserContract(ABC):
    """Port for extracting plain text from a raw document.

    The Phase 9 default handles plain text only. PDF/HTML/DOCX parsing (and the
    table-extraction headaches that come with financial PDFs) is deliberately
    deferred behind this contract — add a parser adapter later without touching
    the ingestion pipeline.
    """

    @abstractmethod
    def parse(
        self,
        content: str,
        content_type: str = "text/plain",
    ) -> str:
        raise NotImplementedError
