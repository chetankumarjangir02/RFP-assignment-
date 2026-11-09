"""Extraction agent(s): fill the 20 fields using ONLY retrieved evidence (spec Part D).

Split into field-group specialists that the orchestrator runs concurrently. Guardrail:
no evidence -> value=None, notes="Not found in documents" (never guess).
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from app.agents.llm import complete_structured
from app.agents.retrieval_agent import format_evidence, retrieve
from app.models.bid_record import FieldValue
from app.observability.logging import log_agent_step
from config.settings import settings

FIELD_GROUPS: dict[str, list[str]] = {
    "dates_logistics": [
        "Due Date", "Delivery Date", "Pre Bid Meeting", "Installation",
        "Bid Submission Type",
    ],
    "commercial_legal": [
        "Bid Bond Requirement", "Payment Terms", "Term of Bid",
        "Any Additional Documentation Required", "Contract or Cooperative to use",
    ],
    "product_specs": [
        "Model_no", "Part_no", "Product", "Product Specification",
        "MFG for Registration",
    ],
    "identity": [
        "Bid Number", "Title", "company_name", "contact_info", "Bid Summary",
    ],
}

# Retrieval hints per field (improves recall over the bare field name).
FIELD_QUERIES: dict[str, str] = {
    "Bid Number": "solicitation number PORFP number RFP number official bid identifier reference",
    "Title": "bid title project title name of the solicitation subject of this RFP",
    "Due Date": "submission deadline due date closing date time",
    "Bid Submission Type": "how to submit bid electronic portal sealed email",
    "Term of Bid": "contract term duration renewal options",
    "Pre Bid Meeting": "pre-bid meeting date time location mandatory",
    "Installation": "installation deployment imaging services required",
    "Bid Bond Requirement": "bid bond security amount percentage required",
    "Delivery Date": "delivery date delivery window after award",
    "Payment Terms": "payment terms net 30 invoicing invoice submission days after delivery",
    "Any Additional Documentation Required": "required affidavits forms certificates insurance W-9",
    "MFG for Registration": "manufacturer name brand authorized reseller the bidder must be registered with",
    "Contract or Cooperative to use": "cooperative state contract vehicle",
    "Model_no": "model number model #",
    "Part_no": "part number SKU catalog number",
    "Product": "product name quantity items requested",
    "contact_info": "procurement contact name email phone buyer",
    "company_name": "issuing organization agency district buyer name who issued this solicitation",
    "Bid Summary": "overview scope of work purpose objective of this solicitation what is being procured",
    "Product Specification": "technical specifications CPU RAM storage display warranty",
}

# Precise definitions for fields whose name alone is ambiguous to the extractor LLM.
# These are field DEFINITIONS (generalizable), never per-bid values or facts.
FIELD_DESCRIPTIONS: dict[str, str] = {
    "Title": (
        "The title/name of this solicitation or RFP (the subject line describing what "
        "is being procured), usually on the cover page or the bid portal header."
    ),
    "company_name": (
        "The organization that ISSUED this solicitation — the buyer/agency/district/"
        "entity requesting bids (not a vendor). Infer it from the issuer named on the "
        "cover page, header, or contact email domain if stated in the evidence."
    ),
    "contact_info": (
        "The procurement/point-of-contact details for this solicitation: name, email, "
        "and/or phone of the buyer or question contact."
    ),
    "Bid Number": (
        "The official solicitation / RFP / PORFP identifier a bidder references when "
        "responding (e.g. 'JA-207652' or '#E20P4600040'). This is NOT an internal "
        "project, eMMA, eMMA/BPM, or accounting number — prefer the number labeled as "
        "the solicitation, RFP, PORFP, or bid number."
    ),
    "MFG for Registration": (
        "The manufacturer(s) / brand the bidder must be registered with or an authorized "
        "reseller of (e.g. a stated 'Manufacturer Name', or a requirement to be an "
        "'authorized reseller for <brand>'). Return the manufacturer name(s)."
    ),
    "Payment Terms": (
        "Payment and invoicing conditions: net terms (e.g. Net 30), when/how invoices "
        "are submitted, and any payment timing requirements stated in the documents."
    ),
}

# Fields whose answer reliably lives in a specific doc_type. Retrieval is BIASED toward
# it first (header/identity info lives on the bid portal page and RFP cover), with a
# fallback to all docs so bids lacking that doc_type still work. Generalizable: every
# BidNet page carries a title + issuing agency regardless of the specific bid.
FIELD_DOC_TYPE_HINTS: dict[str, str] = {
    "Title": "bid_page",
    "company_name": "bid_page",
    "Bid Number": "bid_page",
}


class _Extracted(BaseModel):
    value: Optional[str] = None
    confidence: float = 0.0
    reasoning: Optional[str] = None


_SYSTEM = (
    "You extract a single RFP field from the provided evidence passages only. Use ONLY "
    "the evidence. If it does not contain the answer, set value to null. Never guess."
)

# A null means "not found" — the model's self-reported certainty about an ABSENCE is
# unreliable, so cap it. This keeps not-found fields from reading as 100% certain.
_ABSENCE_CONFIDENCE_CAP = 0.5


def _retrieve_for_field(field: str, bid_id: str, top_k: int):
    """Retrieve evidence for a field, biasing toward its preferred doc_type when one is
    declared, then falling back to an unfiltered search if that pool is empty/thin.

    The doc_type bias boosts recall for header/identity fields without hard-coding any
    bid-specific value; the fallback keeps it robust for bids lacking that doc_type.
    """
    query = FIELD_QUERIES.get(field, field)
    doc_type = FIELD_DOC_TYPE_HINTS.get(field)

    if doc_type:
        biased = retrieve(query, bid_id=bid_id, top_k=top_k, doc_type=doc_type)
        unfiltered = retrieve(query, bid_id=bid_id, top_k=top_k)
        # Lead with the biased (header) passages, then top up from the full index.
        seen = {(e.metadata.file_name, e.metadata.page_number, e.text) for e in biased}
        merged = list(biased)
        for e in unfiltered:
            key = (e.metadata.file_name, e.metadata.page_number, e.text)
            if key not in seen:
                merged.append(e)
                seen.add(key)
        return merged[:top_k]

    return retrieve(query, bid_id=bid_id, top_k=top_k)


def extract_field(field: str, bid_id: str) -> FieldValue:
    """Retrieve evidence for one field and extract a cited value via the LLM."""
    # Bid Summary is a synthesized field, not a lookup — handle it separately.
    if field == "Bid Summary":
        return generate_bid_summary(bid_id)

    with log_agent_step("extraction_agent", field=field, bid_id=bid_id) as step:
        evidence = _retrieve_for_field(field, bid_id, settings.default_top_k)
        step["tool_calls"] = [{"tool": "search", "hits": len(evidence)}]

        if not evidence:
            return FieldValue(value=None, sources=[], confidence=0.0,
                              notes="Not found in documents")

        context = format_evidence(evidence)
        definition = FIELD_DESCRIPTIONS.get(field)
        def_block = f"\nField definition: {definition}\n" if definition else ""
        prompt = (
            f"Field to extract: {field}{def_block}\n"
            f"Evidence passages:\n{context}\n\n"
            f"Extract the value for '{field}'. If absent, value = null."
        )
        try:
            res = complete_structured(prompt, _Extracted, system=_SYSTEM)
        except Exception as e:  # LLM/JSON failure -> safe not-found, don't crash
            step["error"] = str(e)
            return FieldValue(value=None, sources=[], confidence=0.0,
                              notes=f"Extraction error: {e}")

        if res.value in (None, "", "null", "N/A"):
            return FieldValue(
                value=None, sources=[],
                confidence=min(max(res.confidence, 0.0), _ABSENCE_CONFIDENCE_CAP),
                notes="Not found in documents")

        # cite the retrieved passages the answer was grounded in (top few)
        sources = [ev.citation() for ev in evidence[:3]]
        step["output"] = str(res.value)[:120]
        return FieldValue(
            value=res.value,
            sources=sources,
            confidence=min(max(res.confidence, 0.0), 1.0),
            notes=res.reasoning,
        )


class _Summary(BaseModel):
    summary: Optional[str] = None
    confidence: float = 0.0


_SUMMARY_SYSTEM = (
    "You write a concise, factual summary of an RFP/bid using ONLY the provided evidence "
    "passages. Do not invent details. If the evidence is insufficient, set summary to null."
)


def generate_bid_summary(bid_id: str) -> FieldValue:
    """Synthesize a 3-6 sentence Bid Summary from broadly-retrieved overview passages.

    Unlike the other fields this is a *generation* step, not a lookup: it pulls the
    scope/purpose/what-is-being-procured passages and asks the LLM to summarize them,
    grounded in (and cited to) that evidence.
    """
    with log_agent_step("extraction_agent", field="Bid Summary", bid_id=bid_id) as step:
        # Wider retrieval than a point lookup: a good summary needs broader context.
        top_k = max(settings.default_top_k * 2, 8)
        evidence = retrieve(
            "overview purpose scope of work objective what is being procured solicitation summary",
            bid_id=bid_id,
            top_k=top_k,
        )
        step["tool_calls"] = [{"tool": "search", "hits": len(evidence)}]

        if not evidence:
            return FieldValue(value=None, sources=[], confidence=0.0,
                              notes="Not found in documents")

        context = format_evidence(evidence)
        prompt = (
            "Write a 3-6 sentence summary of this solicitation covering: who is issuing "
            "it, what is being procured, and any notable scope/terms. Use ONLY the "
            f"evidence below.\n\nEvidence passages:\n{context}\n\n"
            "If the evidence is insufficient to summarize, set summary to null."
        )
        try:
            res = complete_structured(prompt, _Summary, system=_SUMMARY_SYSTEM)
        except Exception as e:
            step["error"] = str(e)
            return FieldValue(value=None, sources=[], confidence=0.0,
                              notes=f"Summary generation error: {e}")

        if res.summary in (None, "", "null", "N/A"):
            return FieldValue(
                value=None, sources=[],
                confidence=min(max(res.confidence, 0.0), _ABSENCE_CONFIDENCE_CAP),
                notes="Not found in documents")

        sources = [ev.citation() for ev in evidence[:3]]
        step["output"] = str(res.summary)[:120]
        return FieldValue(
            value=res.summary,
            sources=sources,
            confidence=min(max(res.confidence, 0.0), 1.0),
            notes="Generated from retrieved overview passages.",
        )
