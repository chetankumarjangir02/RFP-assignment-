"""BM25 keyword index (rank-bm25). Catches exact bid/part/model numbers that dense
search misses. Persisted to disk (pickle) alongside the Chroma store.
"""
from __future__ import annotations

import pickle
import re
from pathlib import Path

from app.models.documents import Chunk, ChunkMetadata
from app.models.evidence import Evidence
from config.settings import settings

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _matches(meta: ChunkMetadata, where: dict | None) -> bool:
    if not where:
        return True
    data = meta.model_dump(mode="json")
    return all(data.get(k) == v for k, v in where.items())


class BM25Index:
    def __init__(self) -> None:
        self._path = Path(settings.chroma_dir).parent / "bm25.pkl"
        # Each record: {"chunk_id", "text", "tokens", "metadata": dict}
        self._records: list[dict] = []
        self._bm25 = None
        if self._path.exists():
            self._records = pickle.loads(self._path.read_bytes())
            self._rebuild()

    def _rebuild(self) -> None:
        from rank_bm25 import BM25Okapi

        if self._records:
            self._bm25 = BM25Okapi([r["tokens"] for r in self._records])

    def _persist(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_bytes(pickle.dumps(self._records))

    def add(self, chunks: list[Chunk]) -> None:
        """Add chunks to the keyword corpus (idempotent on chunk_id)."""
        if not chunks:
            return
        existing = {r["chunk_id"] for r in self._records}
        for c in chunks:
            if c.chunk_id in existing:
                continue
            self._records.append(
                {
                    "chunk_id": c.chunk_id,
                    "text": c.text,
                    "tokens": _tokenize(c.text),
                    "metadata": c.metadata.model_dump(mode="json"),
                }
            )
        self._rebuild()
        self._persist()

    def query(
        self, query: str, top_k: int, where: dict | None = None
    ) -> list[Evidence]:
        """Score corpus against tokenized query; apply same metadata filter as dense."""
        if self._bm25 is None or not self._records:
            return []
        scores = self._bm25.get_scores(_tokenize(query))
        ranked = sorted(
            zip(self._records, scores), key=lambda x: x[1], reverse=True
        )
        out: list[Evidence] = []
        for rec, score in ranked:
            meta = ChunkMetadata.model_validate(rec["metadata"])
            if not _matches(meta, where):
                continue
            out.append(
                Evidence(
                    chunk_id=rec["chunk_id"],
                    text=rec["text"],
                    score=float(score),
                    metadata=meta,
                )
            )
            if len(out) >= top_k:
                break
        return out
