"""Retrieval/Search agent: rewrites/expands queries, calls the SearchEngine tool with
metadata filters + reranking, returns cited evidence. The ONLY path agents use to search.
"""
from __future__ import annotations

from app.models.evidence import Evidence
from app.search.engine import SearchEngine
from app.search.fusion import reciprocal_rank_fusion
from app.search.query_expander import expand_query
from config.settings import settings

_engine = SearchEngine()


def retrieve(
    query: str,
    bid_id: str | None = None,
    top_k: int | None = None,
    doc_type: str | None = None,
    mode: str | None = None,
) -> list[Evidence]:
    """Expand the query, build a metadata filter, call the search engine, fuse results.

    `mode` (vector|keyword|hybrid|hybrid_rerank) overrides the engine default; it lets the
    eval measure this exact agent retrieval path (expansion + fusion) per configuration.

    Performance: query variants are gathered with the *cheap* (no-rerank) mode and fused;
    the expensive cross-encoder rerank runs ONCE on the fused pool — not once per variant.
    """
    where: dict = {}
    if bid_id:
        where["bid_id"] = bid_id
    if doc_type:
        where["doc_type"] = doc_type
    where = where or None

    variants = expand_query(query)
    effective_mode = mode or settings.default_search_mode

    if len(variants) == 1:
        return _engine.search(query, top_k=top_k, mode=mode, where=where)

    # Gather candidates per variant without reranking (hybrid_rerank -> hybrid here)...
    base_mode = "hybrid" if effective_mode == "hybrid_rerank" else effective_mode
    lists = [_engine.search(v, top_k=top_k, mode=base_mode, where=where) for v in variants]
    fused = reciprocal_rank_fusion(lists)

    # ...then rerank the fused pool a single time when the mode asks for it.
    if effective_mode == "hybrid_rerank":
        from app.search.reranker import rerank

        k = top_k or settings.default_top_k
        return rerank(query, fused[: settings.candidate_k], k)

    return fused[: (top_k or len(fused))]


def format_evidence(evidence: list[Evidence]) -> str:
    """Render retrieved passages as a numbered, cited context block for LLM prompts."""
    lines = []
    for i, ev in enumerate(evidence, 1):
        m = ev.metadata
        lines.append(f"[{i}] ({m.file_name} p.{m.page_number}) {ev.text}")
    return "\n\n".join(lines)
