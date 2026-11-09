"""Chroma vector store: incremental add + filtered query (spec §6.1/§6.2).

Persists to CHROMA_DIR. Metadata is stored alongside each vector so retrieval can
filter by bid_id / doc_type / addendum_number. We pass our own embeddings (bge), so the
collection uses no built-in embedding function.
"""
from __future__ import annotations

from app.models.documents import Chunk, ChunkMetadata
from app.models.evidence import Evidence
from config.settings import settings


def _meta_to_store(meta: ChunkMetadata) -> dict:
    """Chroma metadata values must be str/int/float/bool — drop None keys."""
    return {k: v for k, v in meta.model_dump(mode="json").items() if v is not None}


def _build_where(where: dict | None) -> dict | None:
    """Translate a flat filter into Chroma's where syntax (AND across keys)."""
    if not where:
        return None
    clauses = [{k: v} for k, v in where.items()]
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}


class VectorStore:
    def __init__(self) -> None:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        self._client = chromadb.PersistentClient(
            path=settings.chroma_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        """Upsert chunks. Incremental: adding a new bid does not re-index everything."""
        if not chunks:
            return
        self._collection.upsert(
            ids=[c.chunk_id for c in chunks],
            embeddings=embeddings,
            documents=[c.text for c in chunks],
            metadatas=[_meta_to_store(c.metadata) for c in chunks],
        )

    def has_bid(self, bid_id: str) -> bool:
        """True if any chunk for this bid is already indexed."""
        try:
            got = self._collection.get(where={"bid_id": bid_id}, limit=1)
            return bool(got.get("ids"))
        except Exception:
            return False

    def list_bids(self) -> list[str]:
        """Distinct bid_ids currently indexed (sorted). Used to resolve/normalize input."""
        try:
            got = self._collection.get(include=["metadatas"])
            seen: list[str] = []
            for m in got.get("metadatas") or []:
                b = (m or {}).get("bid_id")
                if b and b not in seen:
                    seen.append(b)
            return sorted(seen)
        except Exception:
            return []

    def query(
        self, embedding: list[float], top_k: int, where: dict | None = None
    ) -> list[Evidence]:
        """Dense search with optional metadata filter (e.g. {'bid_id': 'Bid2'})."""
        res = self._collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            where=_build_where(where),
        )
        ids = res.get("ids", [[]])[0]
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]

        evidence: list[Evidence] = []
        for cid, text, meta, dist in zip(ids, docs, metas, dists):
            evidence.append(
                Evidence(
                    chunk_id=cid,
                    text=text,
                    score=1.0 - float(dist),  # cosine distance -> similarity
                    metadata=ChunkMetadata.model_validate(meta),
                )
            )
        return evidence
