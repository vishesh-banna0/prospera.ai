"""Phase 9 financial research RAG module.

Ingests financial documents (annual reports, earnings calls, presentations,
research reports), chunks and embeds them, and serves semantic retrieval so
later reasoning phases can ground answers in real source passages instead of
an LLM's unverifiable prior knowledge.
"""
