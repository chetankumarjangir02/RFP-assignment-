"""PDF parsing: PyMuPDF for text/layout, pdfplumber for tables (spec Part A).

Returns one Document per page so page_number stays accurate for citations.
"""
from __future__ import annotations

from pathlib import Path

from app.ingestion.cleaner import clean_text, strip_repeated_lines
from app.models.documents import ChunkMetadata, Document


def _tables_to_markdown(tables: list[list[list[str | None]]]) -> list[str]:
    out: list[str] = []
    for tbl in tables:
        rows = [[(c or "").strip().replace("\n", " ") for c in row] for row in tbl if row]
        if not rows:
            continue
        md = [" | ".join(rows[0]), " | ".join("---" for _ in rows[0])]
        md += [" | ".join(r) for r in rows[1:]]
        out.append("\n".join(md))
    return out


def parse_pdf(path: str | Path, bid_id: str) -> list[Document]:
    """Extract page text (PyMuPDF) + tables (pdfplumber). One Document per page."""
    import fitz  # PyMuPDF
    import pdfplumber

    path = Path(path)
    file_name = path.name

    # 1) text per page via PyMuPDF
    page_texts: list[str] = []
    with fitz.open(path) as doc:
        for page in doc:
            page_texts.append(page.get_text("text") or "")

    # 2) tables per page via pdfplumber (best-effort)
    page_tables: list[list[str]] = [[] for _ in page_texts]
    try:
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                if i >= len(page_tables):
                    break
                try:
                    page_tables[i] = _tables_to_markdown(page.extract_tables() or [])
                except Exception:
                    page_tables[i] = []
    except Exception:
        pass  # pdfplumber can choke on some PDFs; keep text-only

    # 3) clean + drop repeated headers/footers across pages
    cleaned = strip_repeated_lines([clean_text(t) for t in page_texts])

    docs: list[Document] = []
    for i, (text, tables) in enumerate(zip(cleaned, page_tables), start=1):
        if not text.strip() and not tables:
            continue  # skip blank/scanned page (logged by caller via empty output)
        docs.append(
            Document(
                text=text,
                tables=tables,
                metadata=ChunkMetadata(
                    bid_id=bid_id, file_name=file_name, page_number=i
                ),
            )
        )
    return docs
