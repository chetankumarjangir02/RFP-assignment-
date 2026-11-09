"""Central configuration. All values come from env vars / .env — never hard-coded in logic.

Import `settings` anywhere:

    from config.settings import settings
    settings.default_top_k
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Silence Chroma's (buggy) anonymized telemetry before chromadb is imported anywhere.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)
# Avoid the HF tokenizers fork-warning when embedding runs inside worker threads.
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- LLM provider: "ollama" (local) | "azure_openai" ---
    llm_provider: str = "ollama"
    llm_temperature: float = 0.0

    # Ollama (local fallback)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b-instruct"

    # Azure OpenAI GPT-4 (used when llm_provider == "azure_openai")
    azure_openai_gpt4_api_key: str = ""
    azure_openai_gpt4_endpoint: str = ""
    azure_openai_gpt4_deployment: str = ""
    azure_openai_gpt4_version: str = "2024-06-01"

    # --- Embeddings / reranker (always local; no re-indexing needed) ---
    embed_model: str = "BAAI/bge-base-en-v1.5"
    reranker_model: str = "BAAI/bge-reranker-base"

    # --- Vector store (Chroma) ---
    chroma_dir: str = "./storage/.chroma"
    chroma_collection: str = "rfp_chunks"

    # --- Retrieval (defaults; overridable per request) ---
    default_top_k: int = 5
    candidate_k: int = 30
    # one of: vector | keyword | hybrid | hybrid_rerank
    # Default is hybrid: on our docs the local bge-reranker-base mis-ranks some queries
    # (e.g. promotes affidavit boilerplate over the due-date passage), so plain hybrid
    # fusion retrieves better. hybrid_rerank stays available for eval comparison.
    default_search_mode: str = "hybrid"

    # --- Chunking ---
    chunk_size: int = 800
    chunk_overlap: int = 150

    # --- Agents ---
    max_validation_retries: int = 2

    # --- Paths ---
    data_dir: str = "./data"
    output_dir: str = "./outputs"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
