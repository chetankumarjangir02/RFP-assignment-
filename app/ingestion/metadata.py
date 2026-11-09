"""Infer document metadata from filenames/content (doc_type, addendum_number, dates).

Heuristic-based so it generalizes to unseen bids — no per-file hard-coding.
"""
from __future__ import annotations

import re

from app.models.documents import DocType

_DATE_PATTERNS = [
    # January 5, 2024  /  Jan 5 2024
    (re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})\b", re.I), "mdy_name"),
    # 01/05/2024  /  1-5-24
    (re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b"), "mdy_num"),
    # 2024-01-05
    (re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"), "iso"),
]

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1
)}


def infer_doc_type(file_name: str, text: str = "") -> DocType:
    """Guess doc_type from filename keywords (falls back to text)."""
    name = file_name.lower()
    hay = name + " " + text[:500].lower()
    if "addendum" in hay or re.search(r"\badd\b", name):
        return DocType.addendum
    if "affidavit" in hay:
        return DocType.affidavit
    if "spec" in hay:
        return DocType.specs
    if any(k in hay for k in ("rfp", "porfp", "solicitation", "request for proposal")):
        return DocType.rfp
    return DocType.rfp  # most main bid PDFs are the RFP; HTML is tagged bid_page by loader


def infer_addendum_number(file_name: str, text: str = "") -> int | None:
    """Pull the addendum number (e.g. 'Addendum 2' -> 2), else None."""
    # Allow spaces, underscores, hyphens or '#' between 'addendum' and the number so it
    # works on real stored filenames like 'Addendum_1_RFP...' or 'Addendum-1.pdf'.
    m = re.search(r"addendum[\s_#-]*(\d+)", (file_name + " " + text[:200]), re.I)
    return int(m.group(1)) if m else None


def infer_document_date(text: str) -> str | None:
    """Find a plausible document date and normalize to ISO (YYYY-MM-DD), or None."""
    for pattern, kind in _DATE_PATTERNS:
        m = pattern.search(text)
        if not m:
            continue
        try:
            if kind == "iso":
                y, mo, d = m.group(1), m.group(2), m.group(3)
            elif kind == "mdy_name":
                mo = _MONTHS[m.group(1)[:3].lower()]
                d, y = m.group(2), m.group(3)
            else:  # mdy_num
                mo, d, y = m.group(1), m.group(2), m.group(3)
                if len(y) == 2:
                    y = "20" + y
            return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
        except (ValueError, KeyError):
            continue
    return None
