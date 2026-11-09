"""Tests for Reciprocal Rank Fusion (implemented, so this runs green now)."""
from __future__ import annotations

from app.models.documents import ChunkMetadata
from app.models.evidence import Evidence
from app.search.fusion import reciprocal_rank_fusion


def _ev(chunk_id: str, score: float = 0.0) -> Evidence:
    return Evidence(
        chunk_id=chunk_id,
        text=f"text-{chunk_id}",
        score=score,
        metadata=ChunkMetadata(bid_id="Bid1", file_name="f.pdf"),
    )


def test_fusion_dedupes_by_chunk_id():
    dense = [_ev("a"), _ev("b")]
    sparse = [_ev("b"), _ev("c")]
    fused = reciprocal_rank_fusion([dense, sparse])
    ids = [e.chunk_id for e in fused]
    assert sorted(ids) == ["a", "b", "c"]
    assert len(ids) == len(set(ids))


def test_fusion_ranks_shared_result_first():
    # 'b' appears in both lists -> should outrank singletons.
    dense = [_ev("a"), _ev("b")]
    sparse = [_ev("b"), _ev("c")]
    fused = reciprocal_rank_fusion([dense, sparse])
    assert fused[0].chunk_id == "b"


def test_fusion_empty_input():
    assert reciprocal_rank_fusion([]) == []
