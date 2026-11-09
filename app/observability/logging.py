"""Structured logging + per-agent step traces (spec §7.2 observability).

`log_agent_step` records input, tool calls, output, tokens and latency for each agent,
which feeds the required example trace deliverable.
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any, Iterator

import structlog

structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()


@contextmanager
def log_agent_step(agent: str, **context: Any) -> Iterator[dict[str, Any]]:
    """Context manager that times an agent step and logs start/end.

    Usage:
        with log_agent_step("retrieval_agent", field="Due Date") as step:
            step["tool_calls"] = [...]
            step["output"] = result
    """
    # Reset the per-thread token meter so this step's LLM calls are attributed to it.
    try:
        from app.agents.llm import get_tokens, reset_tokens

        reset_tokens()
    except Exception:  # observability must never break the pipeline
        get_tokens = None  # type: ignore[assignment]

    step: dict[str, Any] = {"agent": agent, **context}
    start = time.perf_counter()
    logger.info("agent_step_start", **step)
    try:
        yield step
    finally:
        step["latency_ms"] = round((time.perf_counter() - start) * 1000, 1)
        if get_tokens is not None:
            step["tokens"] = get_tokens()
        logger.info("agent_step_end", **step)
