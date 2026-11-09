"""LangGraph wiring (spec §7.2): nodes, edges, shared state, and the Validator feedback
loop. Orchestration entry point used by main.py and the API.

Extract flow:
    ingest -> plan -> extract(pending, parallel) -> reconcile -> validate
              validate --(failed & retries left)--> extract (only failed fields)
              validate --(ok or retries exhausted)--> finalize

QA flow is a direct path (qa_agent) — no multi-step loop needed.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from app.agents.extraction_agent import extract_field
from app.agents.ingestion_agent import ingest
from app.agents.orchestrator import plan, should_retry
from app.agents.qa_agent import answer_question
from app.agents.reconciliation_agent import reconcile
from app.agents.retrieval_agent import _engine, retrieve
from app.agents.validator_agent import validate_field
from app.models.bid_record import BidRecord, ValidationSummary
from app.models.documents import DocType
from app.models.state import GraphState
from app.observability.logging import log_agent_step
from config.settings import settings


# --- nodes -------------------------------------------------------------------
def ingest_node(state: GraphState) -> dict:
    folder = state.get("bid_folder")
    bid_id = state["bid_id"]
    if folder and not _engine.has_bid(bid_id):
        with log_agent_step("ingestion_agent", bid_folder=folder):
            ingest(folder)
    # LangGraph requires every node to update >=1 state key; echo errors (passthrough).
    return {"errors": state.get("errors", [])}


def extract_node(state: GraphState) -> dict:
    bid_id = state["bid_id"]
    rec: BidRecord = state["draft_record"]
    pending = state["pending_fields"]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = pool.map(lambda f: (f, extract_field(f, bid_id)), pending)
    for field, fv in results:
        rec.fields[field] = fv
    return {"draft_record": rec}


def reconcile_node(state: GraphState) -> dict:
    bid_id = state["bid_id"]
    rec: BidRecord = state["draft_record"]
    # Skip entirely when the bid has no addendums (saves ~1 LLM call/field).
    has_addenda = bool(
        retrieve("addendum change", bid_id=bid_id, top_k=1, doc_type=DocType.addendum.value)
    )
    if not has_addenda:
        return {"draft_record": rec}
    for field in state["pending_fields"]:
        updated, change = reconcile(field, rec.fields[field], bid_id)
        rec.fields[field] = updated
        if change:
            rec.addendum_changes.append(change)
    return {"draft_record": rec}


def validate_node(state: GraphState) -> dict:
    rec: BidRecord = state["draft_record"]
    retry_counts = dict(state.get("retry_counts", {}))
    max_retries = settings.max_validation_retries

    failed_now: list[str] = []
    passed = failed = not_found = 0
    for field, fv in rec.fields.items():
        if fv.value is None:
            not_found += 1
            continue
        ok, _reason = validate_field(field, fv)
        if ok:
            passed += 1
        else:
            failed += 1
            if retry_counts.get(field, 0) < max_retries:
                failed_now.append(field)
                retry_counts[field] = retry_counts.get(field, 0) + 1

    rec.validation = ValidationSummary(passed=passed, failed=failed, not_found=not_found)
    return {"draft_record": rec, "pending_fields": failed_now, "retry_counts": retry_counts}


def finalize_node(state: GraphState) -> dict:
    return {"final_record": state["draft_record"]}


# --- graph -------------------------------------------------------------------
def build_graph():
    from langgraph.graph import END, START, StateGraph

    g = StateGraph(GraphState)
    g.add_node("ingest", ingest_node)
    g.add_node("planner", plan)
    g.add_node("extract", extract_node)
    g.add_node("reconcile", reconcile_node)
    g.add_node("validate", validate_node)
    g.add_node("finalize", finalize_node)

    g.add_edge(START, "ingest")
    g.add_edge("ingest", "planner")
    g.add_edge("planner", "extract")
    g.add_edge("extract", "reconcile")
    g.add_edge("reconcile", "validate")
    g.add_conditional_edges("validate", should_retry,
                            {"extract": "extract", "finalize": "finalize"})
    g.add_edge("finalize", END)
    return g.compile()


_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def run_extraction(bid_id: str, bid_folder: str) -> BidRecord:
    """Run the compiled graph in extract mode and return the BidRecord."""
    final = _get_graph().invoke(
        {"mode": "extract", "bid_id": bid_id, "bid_folder": bid_folder},
        config={"recursion_limit": 50},
    )
    return final["final_record"]


def run_qa(question: str, bid_id: str | None = None) -> tuple[str, list]:
    """QA mode: direct retrieve -> answer path."""
    return answer_question(question, bid_id)
