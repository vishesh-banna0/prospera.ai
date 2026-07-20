from __future__ import annotations

import re

DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 150


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    """Split document text into overlapping, word-boundary-aligned chunks.

    Chunking is the quiet make-or-break step of RAG: chunks that are too large
    dilute the embedding (many topics averaged into one vector); too small and
    a passage loses the context needed to answer. Overlap keeps a sentence that
    straddles a boundary retrievable from both neighbouring chunks.

    This is a pure function (no I/O, deterministic) so it can be unit-tested
    and reasoned about in isolation — the same style as the simulator's domain
    policies.
    """

    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    if len(normalized) <= chunk_size:
        return [normalized]

    overlap = max(0, min(overlap, chunk_size - 1))
    step = chunk_size - overlap

    chunks: list[str] = []
    start = 0
    length = len(normalized)
    while start < length:
        end = min(start + chunk_size, length)
        # Snap the cut back to a word boundary unless we're at the very end.
        if end < length:
            boundary = normalized.rfind(" ", start, end)
            if boundary > start:
                end = boundary
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        start = max(start + step, end - overlap)
    return chunks
