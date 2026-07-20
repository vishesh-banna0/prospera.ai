from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC
from datetime import datetime
from enum import StrEnum


# A dense vector representation of a piece of text. Kept as a plain tuple of
# floats so the domain has no dependency on numpy or any embedding library.
Embedding = tuple[float, ...]


class DocumentType(StrEnum):
    ANNUAL_REPORT = "annual_report"
    EARNINGS_CALL = "earnings_call"
    INVESTOR_PRESENTATION = "investor_presentation"
    RESEARCH_REPORT = "research_report"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class ResearchDocument:
    """Metadata about one ingested source document.

    The full text lives in its chunks, not here — this is the catalog entry
    used for listing, filtering, and provenance.
    """

    document_id: str
    title: str
    document_type: DocumentType
    source: str

    symbols: tuple[str, ...] = field(default_factory=tuple)
    sectors: tuple[str, ...] = field(default_factory=tuple)
    published_at: datetime | None = None
    content_hash: str | None = None
    chunk_count: int = 0

    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.document_id.strip():
            raise ValueError("Research document id cannot be blank.")
        if not self.title.strip():
            raise ValueError("Research document title cannot be blank.")
        if self.published_at is not None and self.published_at.tzinfo is None:
            raise ValueError("Research document published_at must be timezone aware.")


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    """One retrievable passage of a document, with its embedding.

    Snapshots the parent document's title, type, symbols, and sectors so a
    retrieved chunk is self-describing for citations and filtering without a
    second lookup.
    """

    chunk_id: str
    document_id: str
    chunk_index: int
    text: str
    embedding: Embedding

    document_type: DocumentType
    document_title: str
    symbols: tuple[str, ...] = field(default_factory=tuple)
    sectors: tuple[str, ...] = field(default_factory=tuple)

    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.chunk_id.strip():
            raise ValueError("Document chunk id cannot be blank.")
        if not self.text.strip():
            raise ValueError("Document chunk text cannot be blank.")
        if not self.embedding:
            raise ValueError("Document chunk embedding cannot be empty.")


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """A chunk paired with its similarity score for one query."""

    chunk: DocumentChunk
    score: float


# Purpose:
# Defines the research-knowledge-base vocabulary for Phase 9 RAG.
#
# Responsibilities:
# - Describe documents and their embedded, retrievable chunks.
# - Keep the domain free of embedding-library and vector-store dependencies.
#
# What Should Not Live Here:
# - Embedding computation (belongs in an embedder adapter).
# - Similarity search / SQL (belongs in a repository adapter).
# - HTTP concerns.
