"""Thin, swappable LLM client. Provider chosen by settings.llm_provider:
  - "ollama"       : local models via Ollama
  - "azure_openai" : Azure OpenAI GPT-4 deployment

Embeddings stay local regardless (see app/search/embedder.py). All credentials come from
env/settings — never hard-coded. Agent code calls complete()/complete_structured().
"""
from __future__ import annotations

import json
import threading
from functools import lru_cache
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

from config.settings import settings

T = TypeVar("T", bound=BaseModel)

# Per-thread token meter so the parallel field-group extraction attributes usage to the
# right agent step. reset at the start of a step, read at the end (see log_agent_step).
_token_meter = threading.local()


def reset_tokens() -> None:
    _token_meter.total = 0


def add_tokens(n: int | None) -> None:
    _token_meter.total = getattr(_token_meter, "total", 0) + int(n or 0)


def get_tokens() -> int:
    return getattr(_token_meter, "total", 0)


@lru_cache
def _ollama():
    import ollama

    return ollama.Client(host=settings.ollama_base_url)


@lru_cache
def _azure():
    from openai import AzureOpenAI

    return AzureOpenAI(
        api_key=settings.azure_openai_gpt4_api_key,
        azure_endpoint=settings.azure_openai_gpt4_endpoint,
        api_version=settings.azure_openai_gpt4_version,
    )


def _messages(prompt: str, system: str | None) -> list[dict]:
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    return msgs


def complete(prompt: str, system: str | None = None) -> str:
    """Plain text completion."""
    if settings.llm_provider == "azure_openai":
        resp = _azure().chat.completions.create(
            model=settings.azure_openai_gpt4_deployment,
            messages=_messages(prompt, system),
            temperature=settings.llm_temperature,
        )
        add_tokens(getattr(resp.usage, "total_tokens", 0) if resp.usage else 0)
        return resp.choices[0].message.content or ""

    resp = _ollama().chat(
        model=settings.ollama_model,
        messages=_messages(prompt, system),
        options={"temperature": settings.llm_temperature},
    )
    add_tokens(resp.get("prompt_eval_count", 0) + resp.get("eval_count", 0))
    return resp["message"]["content"]


def _chat_json(messages: list[dict]) -> str:
    """One JSON-constrained chat call for the active provider."""
    if settings.llm_provider == "azure_openai":
        resp = _azure().chat.completions.create(
            model=settings.azure_openai_gpt4_deployment,
            messages=messages,
            temperature=settings.llm_temperature,
            response_format={"type": "json_object"},
        )
        add_tokens(getattr(resp.usage, "total_tokens", 0) if resp.usage else 0)
        return resp.choices[0].message.content or ""
    resp = _ollama().chat(
        model=settings.ollama_model,
        messages=messages,
        format="json",
        options={"temperature": settings.llm_temperature},
    )
    add_tokens(resp.get("prompt_eval_count", 0) + resp.get("eval_count", 0))
    return resp["message"]["content"]


def complete_structured(prompt: str, schema: Type[T], system: str | None = None) -> T:
    """Structured output: ask for JSON matching `schema`, validate, repair once.

    Raises the last error if both attempts fail — callers catch and fall back gracefully.
    """
    schema_hint = json.dumps(schema.model_json_schema().get("properties", {}), indent=2)
    base = (
        f"{prompt}\n\nReturn ONLY a JSON object with these fields:\n{schema_hint}\n"
        "No prose, no markdown fences — just the JSON object."
    )
    messages = _messages(base, system)

    last_err: Exception | None = None
    for _ in range(2):
        content = _chat_json(messages)
        try:
            return schema.model_validate_json(content)
        except (ValidationError, json.JSONDecodeError) as e:
            last_err = e
            messages.append({"role": "assistant", "content": content})
            messages.append(
                {"role": "user", "content": f"That was invalid ({e}). Return corrected JSON only."}
            )
    raise last_err  # type: ignore[misc]
