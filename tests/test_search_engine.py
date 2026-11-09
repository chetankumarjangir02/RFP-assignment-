"""Search-engine tests (spec §9 requires tests for the search component).

Focuses on the keyword (BM25) leg and metadata filtering — the parts that make exact
bid/part/model numbers retrievable and enable 'only Bid2' style scoping. Isolated to a
temp index dir so it never touches the real store; no embeddings/model downloads, so it
stays fast and deterministic. (RRF fusion is covered in test_fusion.py.)
"""
from __future__ import annotations

import pytest

from app.models.documents import Chunk, ChunkMetadata, DocType
from config.settings import settings


def _chunk(cid: str, text: str, bid_id: str, doc_type=DocType.rfp) -> Chunk:
    return Chunk(
        chunk_id=cid,
        text=text,
        metadata=ChunkMetadata(bid_id=bid_id, file_name=f"{bid_id}.pdf", doc_type=doc_type),
    )


@pytest.fixture
def index(tmp_path, monkeypatch):
    """A fresh, empty BM25 index persisted under a temp dir (no real-store pollution)."""
    monkeypatch.setattr(settings, "chroma_dir", str(tmp_path / ".chroma"))
    from app.search.bm25_index import BM25Index

    idx = BM25Index()
    idx.add(
        [
            _chunk("b1-1", "The proposed Dell Latitude 5550 laptop model SI CC7802", "Bid2"),
            _chunk("b1-2", "Dell Thunderbolt 4 Dock part number WD22TB4 quantity 30", "Bid2", DocType.specs),
            _chunk("b2-1", "Student and Staff Computing Devices Chromebook tier 1", "Bid1"),
            _chunk("b2-2", "Bid bond and insurance requirements for the district", "Bid1"),
        ]
    )
    return idx


def test_bm25_exact_number_ranks_first(index):
    """Keyword search nails an exact part number dense search would blur."""
    hits = index.query("WD22TB4", top_k=3)
    assert hits, "expected a keyword hit for the exact part number"
    assert hits[0].chunk_id == "b1-2"
    assert "WD22TB4" in hits[0].text


def test_metadata_filter_restricts_to_bid(index):
    """where={'bid_id': 'Bid1'} must only return Bid1 chunks."""
    hits = index.query("requirements", top_k=10, where={"bid_id": "Bid1"})
    assert hits
    assert all(h.metadata.bid_id == "Bid1" for h in hits)


def test_metadata_filter_by_doc_type(index):
    """Combined filter (bid + doc_type) narrows to the specs chunk only."""
    hits = index.query("Dell", top_k=10, where={"bid_id": "Bid2", "doc_type": "specs"})
    assert all(h.metadata.doc_type == DocType.specs for h in hits)
    assert {h.chunk_id for h in hits} == {"b1-2"}


def test_bm25_top_k_limits_results(index):
    hits = index.query("Dell laptop district", top_k=2)
    assert len(hits) <= 2


def test_bm25_empty_corpus_is_safe(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "chroma_dir", str(tmp_path / ".chroma"))
    from app.search.bm25_index import BM25Index

    assert BM25Index().query("anything", top_k=5) == []
