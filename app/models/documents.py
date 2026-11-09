"""Document + chunk schemas. Metadata here is the backbone of filtering, citations
and addendum reconciliation, so it travels with every chunk from ingestion onward.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DocType(str, Enum):
    bid_page = "bid_page"
    rfp = "rfp"
    addendum = "addendum"
    specs = "specs"
    affidavit = "affidavit"
    unknown = "unknown"


class ChunkMetadata(BaseModel):
    """Attached to every chunk; mirrors spec Part A metadata requirements."""

    bid_id: str
    file_name: str
    doc_type: DocType = DocType.unknown
    addendum_number: Optional[int] = None
    page_number: Optional[int] = None
    document_date: Optional[str] = None  # ISO date string where available
    section: Optional[str] = None  # nearest heading, for heading-aware chunks
    is_table: bool = False


class Document(BaseModel):
    """A parsed source file before chunking."""

    text: str
    metadata: ChunkMetadata
    tables: list[str] = Field(default_factory=list)  # serialized tables (e.g. markdown)


class Chunk(BaseModel):
    """An indexable unit."""

    chunk_id: str
    text: str
    metadata: ChunkMetadata
