"""Query rewriting / expansion (spec §6.2), e.g. 'deadline' -> 'due date, submission
deadline, closing date'. Kept rule-based + optional LLM expansion to stay offline-friendly.
"""
from __future__ import annotations

# Lightweight synonym map for RFP vocabulary; extend as needed. Keys are matched as
# substrings of the query; matched expansions widen keyword (BM25) recall toward the
# vocabulary the answer passages actually use. Generic terms only — never bid-specific.
SYNONYMS: dict[str, list[str]] = {
    "deadline": ["due date", "submission deadline", "closing date"],
    "bond": ["bid bond", "security", "surety"],
    "warranty": ["warranty", "extended warranty", "coverage"],
    "contact": ["point of contact", "POC", "procurement officer", "buyer",
                "email address", "phone number", "direct questions to"],
    "organization": ["issuing agency", "department", "district", "buyer", "entity name"],
    "issuing": ["issuing agency", "department", "district", "buyer", "entity name"],
    "agency": ["agency POC", "department", "district", "point of contact"],
    "manufacturer": ["manufacturer name", "brand", "authorized reseller", "OEM"],
    "payment": ["payment terms", "invoicing", "net 30", "invoice submitted", "days after delivery"],
    "model": ["model number", "part number", "SKU"],
    "delivery": ["delivery date", "delivered within", "days of award", "lead time"],
}


def expand_query(query: str) -> list[str]:
    """Return the original query plus expansion variants for keyword recall."""
    variants = [query]
    low = query.lower()
    for key, syns in SYNONYMS.items():
        if key in low:
            for s in syns:
                if s not in low:
                    variants.append(f"{query} {s}")
    return variants[:6]
