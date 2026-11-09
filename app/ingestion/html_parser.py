"""HTML parsing: trafilatura for main content, BeautifulSoup for bid-info tables."""
from __future__ import annotations

from pathlib import Path

from app.ingestion.cleaner import clean_text
from app.models.documents import ChunkMetadata, DocType, Document


def _tables_to_markdown(soup) -> list[str]:
    out: list[str] = []
    for table in soup.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
            if any(cells):
                rows.append(cells)
        if not rows:
            continue
        width = max(len(r) for r in rows)
        rows = [r + [""] * (width - len(r)) for r in rows]
        md = [" | ".join(rows[0]), " | ".join("---" for _ in range(width))]
        md += [" | ".join(r) for r in rows[1:]]
        out.append("\n".join(md))
    return out


def parse_html(path: str | Path, bid_id: str) -> Document:
    """Extract clean main text (trafilatura) + structured tables (BeautifulSoup)."""
    import trafilatura
    from bs4 import BeautifulSoup

    path = Path(path)
    raw = path.read_text(encoding="utf-8", errors="ignore")

    body = trafilatura.extract(raw, include_tables=True, favor_recall=True) or ""
    soup = BeautifulSoup(raw, "lxml")
    tables = _tables_to_markdown(soup)

    # fall back to visible text if trafilatura returned little
    if len(body.strip()) < 50:
        body = soup.get_text("\n", strip=True)

    return Document(
        text=clean_text(body),
        tables=tables,
        metadata=ChunkMetadata(
            bid_id=bid_id, file_name=path.name, doc_type=DocType.bid_page
        ),
    )
