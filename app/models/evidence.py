"""Retrieval results + citations. Every answer/field must trace back to one of these."""
from __future__ import annotations

from pydantic import BaseModel

from app.models.documents import ChunkMetadata


class Citation(BaseModel):
    """The spec requires source file + page for every value."""

    file: str
    page: int | None = None


class Evidence(BaseModel):
    """A ranked passage returned by the search engine."""

    chunk_id: str
    text: str
    score: float
    metadata: ChunkMetadata

    def citation(self) -> Citation:
        return Citation(file=self.metadata.file_name, page=self.metadata.page_number)
