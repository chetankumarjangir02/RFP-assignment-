"""Addendum Reconciliation agent (spec §7.1): compare base RFP vs addendums and apply
the latest valid change per field (e.g. an extended due date overrides the original).
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from app.agents.extraction_agent import FIELD_QUERIES
from app.agents.llm import complete_structured
from app.agents.retrieval_agent import format_evidence, retrieve
from app.models.bid_record import AddendumChange, FieldValue
from app.models.documents import DocType
from app.observability.logging import log_agent_step


class _Override(BaseModel):
    changed: bool = False
    new_value: Optional[str] = None
    addendum_number: Optional[int] = None


_SYSTEM = (
    "You decide whether an addendum changes a specific RFP field. Use ONLY the addendum "
    "evidence. If no addendum changes the field, set changed=false."
)


def reconcile(
    field: str, base: FieldValue, bid_id: str
) -> tuple[FieldValue, AddendumChange | None]:
    """Check addendums for an override of `field`; apply the latest valid change."""
    with log_agent_step("reconciliation_agent", field=field, bid_id=bid_id) as step:
        query = FIELD_QUERIES.get(field, field)
        evidence = retrieve(query, bid_id=bid_id, top_k=4, doc_type=DocType.addendum.value)
        step["tool_calls"] = [{"tool": "search", "hits": len(evidence)}]
        if not evidence:
            return base, None

        context = format_evidence(evidence)
        prompt = (
            f"Field: {field}\nCurrent value: {base.value}\n\n"
            f"Addendum evidence:\n{context}\n\n"
            f"Does any addendum change '{field}'? If yes, give the new value and addendum number."
        )
        try:
            res = complete_structured(prompt, _Override, system=_SYSTEM)
        except Exception as e:
            step["error"] = str(e)
            return base, None

        if not res.changed or res.new_value in (None, "", "null"):
            return base, None

        updated = FieldValue(
            value=res.new_value,
            sources=[ev.citation() for ev in evidence[:2]],
            confidence=max(base.confidence, 0.6),
            notes=f"Updated by Addendum {res.addendum_number} (was: {base.value})",
        )
        change = AddendumChange(
            field=field,
            original_value=base.value,
            updated_value=res.new_value,
            addendum_number=res.addendum_number,
            sources=updated.sources,
        )
        step["output"] = f"{base.value} -> {res.new_value}"
        return updated, change
