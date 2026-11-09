"""Shared LangGraph state (spec §7.2). Holds the plan, retrieved evidence, draft fields,
validation results and final output, passed between agent nodes.
"""
from __future__ import annotations

from typing import Annotated, Literal, Optional, TypedDict

from app.models.bid_record import BidRecord
from app.models.evidence import Evidence

Mode = Literal["extract", "qa"]


def _merge_evidence(
    left: dict[str, list[Evidence]], right: dict[str, list[Evidence]]
) -> dict[str, list[Evidence]]:
    """Reducer so parallel extraction branches can each contribute evidence by field."""
    merged = dict(left)
    for k, v in right.items():
        merged[k] = v
    return merged


class GraphState(TypedDict, total=False):
    # inputs
    mode: Mode
    bid_id: str
    bid_folder: Optional[str]
    question: Optional[str]

    # orchestration
    plan: list[str]
    pending_fields: list[str]
    retry_counts: dict[str, int]

    # working memory
    evidence: Annotated[dict[str, list[Evidence]], _merge_evidence]
    draft_record: Optional[BidRecord]

    # outputs
    answer: Optional[str]
    final_record: Optional[BidRecord]
    errors: list[str]
