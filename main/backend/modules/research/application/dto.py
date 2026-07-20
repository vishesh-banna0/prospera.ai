from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


# ============================================================
# Inputs
# ============================================================


@dataclass(frozen=True, slots=True)
class IngestDocumentRequest:
    title: str
    content: str
    document_type: str = "other"
    source: str = "manual"
    symbols: tuple[str, ...] = ()
    sectors: tuple[str, ...] = ()
    published_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ResearchQueryRequest:
    query: str
    top_k: int = 5
    symbol: str | None = None
    document_type: str | None = None


@dataclass(frozen=True, slots=True)
class DocumentQueryRequest:
    symbol: str | None = None
    document_type: str | None = None
    limit: int = 50
    offset: int = 0


# ============================================================
# Views
# ============================================================


@dataclass(frozen=True, slots=True)
class IngestDocumentView:
    document_id: str
    title: str
    chunk_count: int
    message: str | None = None


@dataclass(frozen=True, slots=True)
class RetrievedChunkView:
    chunk_id: str
    document_id: str
    document_title: str
    document_type: str
    chunk_index: int
    text: str
    score: float
    symbols: tuple[str, ...] = field(default_factory=tuple)
    sectors: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class ResearchContextView:
    query: str
    results: tuple[RetrievedChunkView, ...]
    count: int


@dataclass(frozen=True, slots=True)
class DocumentView:
    document_id: str
    title: str
    document_type: str
    source: str
    symbols: tuple[str, ...] = field(default_factory=tuple)
    sectors: tuple[str, ...] = field(default_factory=tuple)
    published_at: datetime | None = None
    chunk_count: int = 0
    created_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class DocumentsView:
    documents: tuple[DocumentView, ...]
    count: int
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class ResearchStatsView:
    total_documents: int
    total_chunks: int
