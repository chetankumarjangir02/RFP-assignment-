"""Schema sanity tests — run green now and guard the shared contracts."""
from __future__ import annotations

from app.models.bid_record import REQUIRED_FIELDS, BidRecord, FieldValue
from app.models.documents import ChunkMetadata, DocType


def test_required_fields_count():
    # Spec Part D defines exactly 20 fields.
    assert len(REQUIRED_FIELDS) == 20
    assert len(set(REQUIRED_FIELDS)) == 20


def test_not_found_field_is_null_with_note():
    fv = FieldValue(value=None, notes="Not found in documents", confidence=0.0)
    assert fv.value is None
    assert fv.sources == []


def test_bid_record_roundtrip():
    rec = BidRecord(bid_id="Bid1", fields={"Title": FieldValue(value="X", confidence=0.9)})
    dumped = rec.model_dump()
    assert dumped["bid_id"] == "Bid1"
    assert BidRecord.model_validate(dumped).fields["Title"].value == "X"


def test_chunk_metadata_defaults():
    m = ChunkMetadata(bid_id="Bid1", file_name="f.pdf")
    assert m.doc_type == DocType.unknown
    assert m.addendum_number is None
