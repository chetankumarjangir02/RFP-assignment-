"""Walk a bid folder, detect file types, dispatch to parsers, attach metadata.

Entry point: `load_bid_folder(path) -> list[Document]`.
Works on an unseen folder with the same shape (no hard-coded filenames). Failures on
individual files are logged and skipped so one bad file never aborts the run.
"""
from __future__ import annotations

from pathlib import Path

from app.ingestion.html_parser import parse_html
from app.ingestion.metadata import (
    infer_addendum_number,
    infer_doc_type,
    infer_document_date,
)
from app.ingestion.pdf_parser import parse_pdf
from app.models.documents import DocType, Document
from app.observability.logging import logger

_PDF_EXT = {".pdf"}
_HTML_EXT = {".html", ".htm"}


def load_bid_folder(folder: str | Path) -> list[Document]:
    """Parse every supported file in a bid folder into Documents with metadata."""
    folder = Path(folder)
    if not folder.is_dir():
        raise FileNotFoundError(f"Bid folder not found: {folder}")

    bid_id = folder.name
    documents: list[Document] = []

    for file in sorted(folder.iterdir()):
        if not file.is_file() or file.name.startswith("."):
            continue
        ext = file.suffix.lower()
        try:
            if ext in _PDF_EXT:
                docs = parse_pdf(file, bid_id)
                doc_type = infer_doc_type(file.name)
                addn = infer_addendum_number(file.name)
                for d in docs:
                    d.metadata.doc_type = doc_type
                    d.metadata.addendum_number = addn
                    if d.metadata.document_date is None:
                        d.metadata.document_date = infer_document_date(d.text)
                documents.extend(docs)
            elif ext in _HTML_EXT:
                d = parse_html(file, bid_id)  # doc_type set to bid_page inside
                d.metadata.document_date = infer_document_date(d.text)
                documents.append(d)
            else:
                logger.info("ingestion_skip_unsupported", file=file.name)
                continue
            logger.info("ingestion_parsed", file=file.name, ext=ext)
        except Exception as e:  # never abort the whole folder on one bad file
            logger.error("ingestion_failed", file=file.name, error=str(e))
            continue

    if not documents:
        logger.error("ingestion_empty", folder=str(folder))
    return documents
