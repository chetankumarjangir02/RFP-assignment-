"""Paragraph/table-aware chunking with overlap (spec §6.1).

Strategy (justified in README):
  - Body text is packed into ~chunk_size-char chunks on paragraph boundaries, with
    chunk_overlap carried between consecutive chunks to preserve context across splits.
  - Each table is emitted as its OWN chunk (is_table=True) so specification/bid tables
    are never fragmented — important for exact spec/value retrieval.
  - chunk_id is deterministic: "{bid_id}:{file_name}:{page}:{idx}".
"""
from __future__ import annotations

import re

from app.models.documents import Chunk, Document
from config.settings import settings


def _pack_paragraphs(text: str, size: int, overlap: int) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    cur = ""
    for p in paras:
        if len(p) > size:  # hard-split an oversized paragraph with overlap
            if cur:
                chunks.append(cur)
                cur = ""
            step = max(size - overlap, 1)
            for i in range(0, len(p), step):
                chunks.append(p[i : i + size])
            continue
        if cur and len(cur) + len(p) + 2 > size:
            chunks.append(cur)
            # start next chunk with a tail of the previous one for continuity
            tail = cur[-overlap:] if overlap else ""
            cur = (tail + "\n\n" + p).strip()
        else:
            cur = (cur + "\n\n" + p).strip() if cur else p
    if cur:
        chunks.append(cur)
    return chunks


def chunk_document(doc: Document) -> list[Chunk]:
    """Split a Document into overlapping, metadata-carrying chunks (+ table chunks)."""
    m = doc.metadata
    page = m.page_number if m.page_number is not None else 0
    prefix = f"{m.bid_id}:{m.file_name}:{page}"
    chunks: list[Chunk] = []

    for idx, text in enumerate(
        _pack_paragraphs(doc.text, settings.chunk_size, settings.chunk_overlap)
    ):
        chunks.append(
            Chunk(chunk_id=f"{prefix}:{idx}", text=text, metadata=m.model_copy())
        )

    for t_idx, table in enumerate(doc.tables):
        tmeta = m.model_copy(update={"is_table": True})
        chunks.append(
            Chunk(chunk_id=f"{prefix}:t{t_idx}", text=table, metadata=tmeta)
        )

    return chunks
