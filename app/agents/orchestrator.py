"""Orchestrator/Planner node logic (spec §7.1). Builds the plan and drives the validator
feedback loop with bounded retries. The graph wiring lives in graph.py.
"""
from __future__ import annotations

from app.models.bid_record import REQUIRED_FIELDS, BidRecord
from app.models.state import GraphState


def plan(state: GraphState) -> dict:
    """Turn the goal into the initial field worklist + empty draft record."""
    return {
        "plan": [f"extract:{f}" for f in REQUIRED_FIELDS],
        "pending_fields": list(REQUIRED_FIELDS),
        "draft_record": BidRecord(bid_id=state["bid_id"]),
        "retry_counts": {},
        "errors": [],
    }


def should_retry(state: GraphState) -> str:
    """Conditional edge after validation: re-extract failed fields, else finalize."""
    return "extract" if state.get("pending_fields") else "finalize"
