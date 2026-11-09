"""Parsing + ingestion tests (spec §9 requires tests for the parsing component).

Covers metadata inference, text cleaning, and real PDF page extraction — all pure/local,
no LLM or network.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.ingestion.cleaner import clean_text, strip_repeated_lines
from app.ingestion.metadata import (
    infer_addendum_number,
    infer_doc_type,
    infer_document_date,
)
from app.models.documents import DocType


# --- metadata: addendum number -------------------------------------------------
@pytest.mark.parametrize(
    "name,expected",
    [
        ("Addendum 2 RFP JA-207652.pdf", 2),
        ("Addendum_1_RFP_JA-207652.pdf", 1),
        ("Addendum #3.pdf", 3),
        ("JA-207652 Final.pdf", None),
        ("Dell_Laptop_Specs.pdf", None),
    ],
)
def test_infer_addendum_number(name, expected):
    assert infer_addendum_number(name) == expected


# --- metadata: doc_type --------------------------------------------------------
@pytest.mark.parametrize(
    "name,expected",
    [
        ("Addendum 2 RFP.pdf", DocType.addendum),
        ("Mercury_Affidavit.pdf", DocType.affidavit),
        ("Dell_Laptop_Specs.pdf", DocType.specs),
        ("PORFP - Dell Laptop Final.pdf", DocType.rfp),
        ("JA-207652 Student and Staff Computing Devices FINAL.pdf", DocType.rfp),
    ],
)
def test_infer_doc_type(name, expected):
    assert infer_doc_type(name) == expected


# --- metadata: document date normalization ------------------------------------
@pytest.mark.parametrize(
    "text,expected",
    [
        ("Issued on June 10, 2024 by the district", "2024-06-10"),
        ("PROPOSAL DUE DATE 06/10/2024", "2024-06-10"),
        ("date: 2024-06-10", "2024-06-10"),
        ("no date anywhere here", None),
    ],
)
def test_infer_document_date(text, expected):
    assert infer_document_date(text) == expected


# --- cleaner: hyphenation + whitespace ----------------------------------------
def test_cleaner_fixes_hyphenation():
    assert "information" in clean_text("inform-\nation")


def test_cleaner_normalizes_whitespace():
    out = clean_text("a\t\t b   c   \n\n\n\n d ")
    assert "a b c" in out
    assert "\n\n\n" not in out  # 3+ blank lines collapsed


def test_cleaner_empty_is_safe():
    assert clean_text("") == ""
    assert clean_text(None) == ""  # type: ignore[arg-type]


# --- cleaner: repeated header/footer removal ----------------------------------
def test_strip_repeated_lines_removes_boilerplate():
    header = "CONFIDENTIAL - DALLAS ISD"
    pages = [f"{header}\nbody one", f"{header}\nbody two", f"{header}\nbody three"]
    cleaned = strip_repeated_lines(pages, min_repeat=3)
    assert all(header not in p for p in cleaned)
    assert "body one" in cleaned[0]  # real content preserved


# --- real PDF parsing (page numbers + file_name travel with each page) --------
def test_pdf_parser_extracts_pages_with_metadata():
    pdf = Path("data/Bid2/PORFP_-_Dell_Laptop_Final.pdf")
    if not pdf.exists():
        pytest.skip("sample bid PDF not present in ./data")
    from app.ingestion.pdf_parser import parse_pdf

    docs = parse_pdf(pdf, bid_id="Bid2")
    assert len(docs) >= 1
    assert [d.metadata.page_number for d in docs] == list(range(1, len(docs) + 1))
    assert all(d.metadata.file_name == pdf.name for d in docs)
    assert all(d.metadata.bid_id == "Bid2" for d in docs)
    assert any(d.text.strip() for d in docs)  # at least one page has text
