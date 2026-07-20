CREATE TABLE IF NOT EXISTS research_documents (
    document_id VARCHAR(64) PRIMARY KEY,
    title VARCHAR(512) NOT NULL,
    document_type VARCHAR(32) NOT NULL,
    source VARCHAR(255) NOT NULL,
    symbols JSONB NOT NULL DEFAULT '[]'::jsonb,
    sectors JSONB NOT NULL DEFAULT '[]'::jsonb,
    content_hash VARCHAR(64),
    chunk_count INTEGER NOT NULL DEFAULT 0,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_research_documents_document_type
    ON research_documents (document_type);

CREATE INDEX IF NOT EXISTS ix_research_documents_published_at
    ON research_documents (published_at);

CREATE INDEX IF NOT EXISTS ix_research_documents_symbols
    ON research_documents USING GIN (symbols);

CREATE TABLE IF NOT EXISTS research_chunks (
    chunk_id VARCHAR(80) PRIMARY KEY,
    document_id VARCHAR(64) NOT NULL
        REFERENCES research_documents (document_id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    embedding JSONB NOT NULL DEFAULT '[]'::jsonb,
    document_type VARCHAR(32) NOT NULL,
    document_title VARCHAR(512) NOT NULL,
    symbols JSONB NOT NULL DEFAULT '[]'::jsonb,
    sectors JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_research_chunks_document_id
    ON research_chunks (document_id);

CREATE INDEX IF NOT EXISTS ix_research_chunks_document_type
    ON research_chunks (document_type);

CREATE INDEX IF NOT EXISTS ix_research_chunks_symbols
    ON research_chunks USING GIN (symbols);

-- Phase 9 financial research RAG knowledge base.
--
-- research_documents holds catalog metadata; research_chunks holds the
-- retrievable passages and their embedding vectors. document_id is a
-- deterministic hash of (title, source, content), so re-ingesting the same
-- document replaces its chunks (idempotent) rather than duplicating them.
--
-- The default backend stores embeddings as JSON and ranks by cosine similarity
-- in application code. This is correct but O(n) per query; the production
-- scale path is Postgres + pgvector (store embedding as vector, add an
-- ivfflat/hnsw index) or an external Qdrant collection behind the same
-- ResearchRepository contract.
