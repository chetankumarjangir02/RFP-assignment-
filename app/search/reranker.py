"""Cross-encoder reranker (BAAI/bge-reranker-base) over fused candidates (spec §6.2)."""
from __future__ import annotations

from functools import lru_cache

from app.models.evidence import Evidence
from config.settings import settings


@lru_cache
def _model():
    from sentence_transformers import CrossEncoder

    return CrossEncoder(settings.reranker_model)


def rerank(query: str, candidates: list[Evidence], top_k: int) -> list[Evidence]:
    """Re-score (query, passage) pairs and return the top_k by cross-encoder score."""
    if not candidates:
        return []
    pairs = [(query, ev.text) for ev in candidates]
    scores = _model().predict(pairs)
    reranked = [
        ev.model_copy(update={"score": float(s)})
        for ev, s in sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
    ]
    return reranked[:top_k]
