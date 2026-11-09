"""Q&A / Report agent (spec §7.1): answer free-form questions over the bids with citations.

Guardrail: if retrieval is empty/weak, answer 'Not found in documents' instead of guessing.
"""
from __future__ import annotations

from app.agents.llm import complete
from app.agents.prompts import QA_SYSTEM
from app.agents.retrieval_agent import format_evidence, retrieve
from app.models.evidence import Evidence
from app.observability.logging import log_agent_step
from config.settings import settings


def answer_question(
    question: str, bid_id: str | None = None
) -> tuple[str, list[Evidence]]:
    """Retrieve evidence and synthesize a cited answer."""
    with log_agent_step("qa_agent", question=question, bid_id=bid_id) as step:
        evidence = retrieve(question, bid_id=bid_id, top_k=settings.default_top_k)
        step["tool_calls"] = [{"tool": "search", "hits": len(evidence)}]

        if not evidence:
            step["output"] = "not_found"
            return ("Not found in documents.", [])

        context = format_evidence(evidence)
        prompt = (
            f"Evidence passages:\n{context}\n\n"
            f"Question: {question}\n\n"
            "Answer using only the evidence above. Cite sources inline as (file p.N). "
            "If the evidence does not answer the question, say 'Not found in documents.'"
        )
        try:
            answer = complete(prompt, system=QA_SYSTEM)
        except Exception as e:  # LLM/Ollama failure — don't crash the request
            step["error"] = str(e)
            return (f"LLM error: {e}", evidence)

        step["output"] = answer[:200]
        return (answer.strip(), evidence)
