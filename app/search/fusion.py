"""Reciprocal Rank Fusion to merge dense + keyword result lists (spec §6.2)."""
from __future__ import annotations

from app.models.evidence import Evidence


def reciprocal_rank_fusion(
    result_lists: list[list[Evidence]], k: int = 60
) -> list[Evidence]:
    """Merge multiple ranked lists via RRF: score = sum(1 / (k + rank)).

    Deduplicates by chunk_id and returns a single list sorted by fused score.
    This one is fully implemented since it's small and config-independent.
    """
    scores: dict[str, float] = {}
    best: dict[str, Evidence] = {}
    for results in result_lists:
        for rank, ev in enumerate(results):
            scores[ev.chunk_id] = scores.get(ev.chunk_id, 0.0) + 1.0 / (k + rank + 1)
            best.setdefault(ev.chunk_id, ev)

    fused: list[Evidence] = []
    for chunk_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        ev = best[chunk_id].model_copy(update={"score": score})
        fused.append(ev)
    return fused
