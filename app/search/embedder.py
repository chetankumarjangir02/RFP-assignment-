"""Local embeddings via sentence-transformers (BAAI/bge-base-en-v1.5)."""
from __future__ import annotations

from functools import lru_cache

from config.settings import settings


@lru_cache
def _model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.embed_model)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts. bge models benefit from a query prefix at search time."""
    return _model().encode(texts, normalize_embeddings=True).tolist()


def embed_query(query: str) -> list[float]:
    # bge recommends this instruction prefix for retrieval queries.
    prefixed = f"Represent this sentence for searching relevant passages: {query}"
    return _model().encode([prefixed], normalize_embeddings=True)[0].tolist()
