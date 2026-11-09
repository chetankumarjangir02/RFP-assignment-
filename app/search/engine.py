"""SearchEngine facade (spec §6) — the single grounding layer.

Used BOTH standalone (API/CLI) and as the tool the agents call. Agents never touch
Chroma/BM25 directly; they go through `search()`.

Search mode is a tunable knob with a sensible default (settings.default_search_mode),
overridable per call so eval/run_eval.py can compare configs:
    vector | keyword | hybrid | hybrid_rerank
"""
from __future__ import annotations

from app.models.documents import Chunk
from app.models.evidence import Evidence
from app.search.bm25_index import BM25Index
from app.search.embedder import embed_query, embed_texts
from app.search.fusion import reciprocal_rank_fusion
from app.search.reranker import rerank
from app.search.vector_store import VectorStore
from config.settings import settings


class SearchEngine:
    def __init__(self) -> None:
        self.vector = VectorStore()
        self.bm25 = BM25Index()

    # --- indexing (incremental) ---
    def index(self, chunks: list[Chunk]) -> int:
        """Add chunks to both indexes. Returns count indexed."""
        embeddings = embed_texts([c.text for c in chunks])
        self.vector.add(chunks, embeddings)
        self.bm25.add(chunks)
        return len(chunks)

    def has_bid(self, bid_id: str) -> bool:
        return self.vector.has_bid(bid_id)

    def list_bids(self) -> list[str]:
        """Distinct indexed bid_ids (sorted)."""
        return self.vector.list_bids()

    def resolve_bid(self, bid_id: str | None) -> str | None:
        """Map an arbitrary user-typed bid_id to the real indexed one.

        Matching is tolerant: exact first, then case-insensitive with spaces, hyphens
        and underscores collapsed — so 'bid 3', 'Bid3', 'BID_3' all resolve to 'bid_3'.
        Returns None when nothing indexed matches.
        """
        if not bid_id:
            return None
        bids = self.list_bids()
        if bid_id in bids:
            return bid_id

        def norm(s: str) -> str:
            return "".join(ch for ch in s.lower() if ch.isalnum())

        target = norm(bid_id)
        for b in bids:
            if norm(b) == target:
                return b
        return None

    # --- retrieval ---
    def search(
        self,
        query: str,
        top_k: int | None = None,
        mode: str | None = None,
        where: dict | None = None,
    ) -> list[Evidence]:
        """Return ranked, cited evidence.

        `where` is a metadata filter, e.g. {'bid_id': 'Bid2', 'doc_type': 'specs'}.
        """
        top_k = top_k or settings.default_top_k
        mode = mode or settings.default_search_mode
        cand_k = max(settings.candidate_k, top_k)

        if mode == "vector":
            return self.vector.query(embed_query(query), top_k, where)
        if mode == "keyword":
            return self.bm25.query(query, top_k, where)

        # hybrid / hybrid_rerank: fetch candidate pools from both, fuse
        dense = self.vector.query(embed_query(query), cand_k, where)
        sparse = self.bm25.query(query, cand_k, where)
        fused = reciprocal_rank_fusion([dense, sparse])

        if mode == "hybrid":
            return fused[:top_k]
        if mode == "hybrid_rerank":
            return rerank(query, fused[:cand_k], top_k)

        raise ValueError(f"Unknown search mode: {mode}")
