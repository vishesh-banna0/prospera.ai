from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query

from backend.api.dependencies import get_research_service
from backend.modules.research.application.dto import (
    DocumentQueryRequest,
    DocumentView,
    DocumentsView,
    IngestDocumentRequest,
    IngestDocumentView,
    ResearchContextView,
    ResearchQueryRequest,
    ResearchStatsView,
)
from backend.modules.research.application.services import ResearchService

router = APIRouter(prefix="/research", tags=["research"])


@router.post("/documents", response_model=IngestDocumentView)
async def ingest_document(
    request: IngestDocumentRequest,
    service: ResearchService = Depends(get_research_service),
) -> IngestDocumentView:
    """Ingest a document: parse, chunk, embed, and store it for retrieval."""
    try:
        return await service.ingest_document(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/search", response_model=ResearchContextView)
async def search_research(
    request: ResearchQueryRequest,
    service: ResearchService = Depends(get_research_service),
) -> ResearchContextView:
    """Semantic search: return the most relevant document passages for a query."""
    try:
        return await service.search(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/documents", response_model=DocumentsView)
async def list_documents(
    symbol: str | None = Query(
        default=None,
        description="Ticker symbol filter, for example AAPL.",
    ),
    document_type: str | None = Query(
        default=None,
        description="Document type filter, e.g. annual_report, earnings_call.",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: ResearchService = Depends(get_research_service),
) -> DocumentsView:
    """List ingested research documents."""
    try:
        return await service.list_documents(
            DocumentQueryRequest(
                symbol=symbol,
                document_type=document_type,
                limit=limit,
                offset=offset,
            )
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stats", response_model=ResearchStatsView)
async def get_research_stats(
    service: ResearchService = Depends(get_research_service),
) -> ResearchStatsView:
    """Get document and chunk counts for the research knowledge base."""
    return await service.get_stats()


@router.get("/documents/{document_id}", response_model=DocumentView)
async def get_document(
    document_id: str,
    service: ResearchService = Depends(get_research_service),
) -> DocumentView:
    """Get one research document's metadata by id."""
    try:
        return await service.get_document(document_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


"""
Purpose:
Expose the Phase 9 research RAG knowledge base over HTTP.

Endpoints:
- POST /research/documents: Ingest (parse -> chunk -> embed -> store)
- POST /research/search: Semantic retrieval of relevant passages
- GET /research/documents: List ingested documents
- GET /research/documents/{document_id}: Fetch one document's metadata
- GET /research/stats: Document/chunk counts

What Should Not Live Here:
- Embedding computation (belongs in an embedder adapter)
- Chunking or similarity math
- Persistence queries
"""
