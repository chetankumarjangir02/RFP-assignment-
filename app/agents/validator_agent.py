"""Validator/Critic agent (spec §7.1): check each field for evidence support, format and
consistency. Failed fields are sent back to the orchestrator for bounded re-extraction.
"""
from __future__ import annotations

import re

from app.models.bid_record import FieldValue

_DATE_FIELDS = {"Due Date", "Delivery Date"}
_DATE_HINT = re.compile(r"\d{4}|\d{1,2}[/-]\d{1,2}|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec", re.I)


def validate_field(field: str, value: FieldValue) -> tuple[bool, str]:
    """Return (passed, reason).

    Rules:
      - a non-null value MUST have >=1 citation (anti-hallucination guardrail)
      - date fields must look date-like
      - null values are 'passed' as a legitimate 'not found' result
    """
    if value.value is None:
        return True, "null (not found) accepted"

    if not value.sources:
        return False, "non-null value has no citation"

    if field in _DATE_FIELDS and not _DATE_HINT.search(str(value.value)):
        return False, "date field has no recognizable date"

    if isinstance(value.value, str) and len(value.value.strip()) == 0:
        return False, "empty string value"

    return True, "ok"
