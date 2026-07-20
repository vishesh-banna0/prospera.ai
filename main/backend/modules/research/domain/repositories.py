from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from backend.modules.research.domain.entities import DocumentChunk
from backend.modules.research.domain.entities import DocumentType
from backend.modules.research.domain.entities import Embedding
from backend.modules.research.domain.entities import ResearchDocument
from backend.modules.research.domain.entities import RetrievedChunk


class ResearchRepository(ABC):
    """Persistence + retrieval contract for the research knowledge base.

    One cohesive store for both documents and their chunks, including the
    similarity search that powers retrieval. The default SQL adapter does
    cosine similarity in Python over stored vectors; a future Qdrant adapter
    implements the same contract for scale.
    """

    @abstractmethod
    async def save_document(
        self,
        document: ResearchDocument,
        chunks: list[DocumentChunk],
    ) -> None:
        """Upsert the document and replace its chunks (idempotent re-ingest)."""
        raise NotImplementedError

    @abstractmethod
    async def get_document(
        self,
        document_id: str,
    ) -> ResearchDocument | None:
        raise NotImplementedError

    @abstractmethod
    async def list_documents(
        self,
        symbol: str | None = None,
        document_type: DocumentType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ResearchDocument]:
        raise NotImplementedError

    @abstractmethod
    async def search_chunks(
        self,
        query_embedding: Embedding,
        top_k: int = 5,
        symbol: str | None = None,
        document_type: DocumentType | None = None,
    ) -> list[RetrievedChunk]:
        raise NotImplementedError

    @abstractmethod
    async def get_stats(
        self,
    ) -> dict[str, int]:
        raise NotImplementedError
