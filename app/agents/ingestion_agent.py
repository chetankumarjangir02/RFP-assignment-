"""Ingestion agent: parse a bid folder, chunk, and index into the SearchEngine."""
from __future__ import annotations

from app.ingestion.chunker import chunk_document
from app.ingestion.loader import load_bid_folder
from app.search.engine import SearchEngine

_engine = SearchEngine()


def ingest(bid_folder: str) -> int:
    """Parse -> chunk -> index. Returns number of chunks indexed.

    TODO: log failures per file; skip unreadable without aborting the run.
    """
    docs = load_bid_folder(bid_folder)
    chunks = [c for d in docs for c in chunk_document(d)]
    return _engine.index(chunks)
