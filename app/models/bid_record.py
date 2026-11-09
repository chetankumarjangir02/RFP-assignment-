"""The structured extraction output (spec Part D). One BidRecord -> one JSON file per bid.

Every field carries value + sources + confidence + notes. `value=None` with a reason in
`notes` means "Not found in documents" (guardrail: never guess).
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.evidence import Citation

# The 20 required fields, in spec order. Used to build/validate the record.
REQUIRED_FIELDS: list[str] = [
    "Bid Number",
    "Title",
    "Due Date",
    "Bid Submission Type",
    "Term of Bid",
    "Pre Bid Meeting",
    "Installation",
    "Bid Bond Requirement",
    "Delivery Date",
    "Payment Terms",
    "Any Additional Documentation Required",
    "MFG for Registration",
    "Contract or Cooperative to use",
    "Model_no",
    "Part_no",
    "Product",
    "contact_info",
    "company_name",
    "Bid Summary",
    "Product Specification",
]


class FieldValue(BaseModel):
    value: Any | None = None
    sources: list[Citation] = Field(default_factory=list)
    confidence: float = 0.0
    notes: Optional[str] = None


class AddendumChange(BaseModel):
    field: str
    original_value: Any | None = None
    updated_value: Any | None = None
    addendum_number: Optional[int] = None
    sources: list[Citation] = Field(default_factory=list)


class ValidationSummary(BaseModel):
    passed: int = 0
    failed: int = 0
    not_found: int = 0


class BidRecord(BaseModel):
    bid_id: str
    fields: dict[str, FieldValue] = Field(default_factory=dict)
    addendum_changes: list[AddendumChange] = Field(default_factory=list)
    validation: ValidationSummary = Field(default_factory=ValidationSummary)
