# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status: implemented

The platform is built and runnable: ingestion/parsing, the hybrid search engine, the
LangGraph multi-agent system, the FastAPI API, the React UI, eval harness and tests all
exist. Per-bid JSON outputs, the retrieval eval report, a Q&A log and an extraction trace
are committed under `outputs/`, `eval/results/` and `docs/`. The sections below describe
the intended design and invariants — read `README.md` for how to run each mode and the
design rationale, and the PDF for the authoritative spec.

Note: the enclosing git repository root is the user's home directory, not this folder. Before committing, confirm with the user whether this assignment should become its own repo (`git init` here) — otherwise commits land in the home-directory repo.

## What this project is

An **RFP Intelligence Platform**: ingest bid/RFP documents (HTML + PDF, including addendums), make them searchable via a RAG search engine, and run a multi-agent system over that search engine to (a) extract a structured JSON record per bid with per-field citations and confidence, and (b) answer free-form questions with citations.

Input unit is a **bid folder** (e.g. `Bid1/`, `Bid2/`) containing a BidNet HTML page plus several PDFs (RFP, addendums, specs, affidavits). The solution **must generalize to unseen bid folders without code changes** — never hard-code facts, filenames, field values, or per-bid logic.

## Expected structure and run model (from spec §9)

Target module layout: `ingestion/`, `search/`, `agents/`, `api/`, `eval/`, `tests/`. Python 3.10+.

- Must be runnable with **one command** after setup, e.g. `python main.py --bid ./Bid1` or `docker compose up`.
- All API keys and model names come from **env vars or a config file** — no secrets in code, no model names hard-coded in logic.
- Unit tests required at minimum for the **parsing** and **search** components.
- When build/lint/test commands are established, record them here (how to run the full suite and a single test).

## Architecture (the pipeline the agents operate)

```
HTML/PDF files → Ingestion & Parsing → Chunking + Embedding → Search Index (vector + keyword)
                                                                      ↑ (search tool)
User goal/question → Orchestrator → Retrieval → Extraction(s) → Addendum Reconciliation → Validator → JSON/answer
```

Three things tie the whole system together — most cross-file changes touch them:

1. **The search engine is the single grounding layer.** Every agent answer must come from retrieved, cited passages. Agents call the search engine **as a tool**; they are never handed whole documents in the prompt. A citation = source file + page number + chunk text, carried end-to-end so any value traces back.

2. **Metadata travels with every chunk.** Each chunk/document carries `bid_id`, `file_name`, `doc_type` (`bid_page` | `rfp` | `addendum` | `specs` | `affidavit`), `addendum_number`, `page_number`, and document date when available. Retrieval filtering (e.g. "only Bid2 specs"), addendum reconciliation, and citations all depend on this metadata being correct from ingestion onward. Indexing must be **incremental** — adding a bid folder must not re-index everything.

3. **Shared state object drives orchestration.** A single state/memory object holds the plan, retrieved evidence, draft fields, validation results, and final output, and is passed between agents. The **Validator→Orchestrator feedback loop** re-runs retrieval/extraction for rejected fields with a **bounded retry count** (avoid infinite loops). All agent-to-agent messages use structured outputs (Pydantic / JSON schema).

### Retrieval must be hybrid, not a single vector lookup
Dense semantic search **fused** with keyword search (BM25 or similar) via RRF or weighted scores — keyword matching matters for exact bid/part/model numbers. Plus metadata filtering, re-ranking (cross-encoder or LLM), and query rewriting/expansion.

### Agent roles (single responsibility each)
Orchestrator/Planner, Ingestion, Retrieval/Search, Extraction (may split into field-group specialists that run concurrently), Addendum Reconciliation, Validator/Critic, Q&A/Report. You may merge/split/add agents **if the rationale is documented**.

## Hard rules (these are graded and easy to violate)

- **No hallucination / mandatory citations.** Every extracted value needs ≥1 citation. When a fact isn't in the documents, return `null` with a reason ("Not found in documents") and still a confidence — never guess.
- **Addendums override the base RFP.** For each field, apply the **latest valid** addendum change (e.g. an extended due date wins over the original). Track what changed where.
- **Fail gracefully, never crash the pipeline.** Handle scanned/empty/unreadable pages, LLM timeouts, bad JSON, and empty retrieval; log these cases.
- **Observability.** Log each agent step: input, tool calls, output, tokens, latency. One full extraction trace is a required deliverable.

## Extraction output contract (spec §8)

One JSON file per bid. Twenty fields (Bid Number, Title, Due Date, Bid Submission Type, Term of Bid, Pre Bid Meeting, Installation, Bid Bond Requirement, Delivery Date, Payment Terms, Any Additional Documentation Required, MFG for Registration, Contract or Cooperative to use, Model_no, Part_no, Product, contact_info, company_name, Bid Summary, Product Specification). Each field is an object with `value`, `sources` (list of `{file, page}`), `confidence`, and `notes`; plus top-level `bid_id`, `addendum_changes`, and a `validation` summary (`passed`/`failed`/`not_found`). See the PDF §8.1 for the exact shape.

## Supported modes
- **Extraction mode** — given a bid folder, produce the full structured JSON record.
- **Q&A mode** — answer natural-language questions with citations (including cross-bid comparisons and "what changed in Addendum N" questions).

## Evaluation deliverables to keep in sync
A retrieval eval set of **≥15 question→expected-passage pairs** across both bids, reporting Recall@k and MRR/nDCG for **at least two configs** (e.g. vector-only vs hybrid vs hybrid+reranker), with the results table in the README. Also required: README with design-decision rationale (chunking, embedding model, retrieval strategy, agent framework choice — all must be justified), architecture diagram, per-bid JSON outputs, a ≥10-question cited Q&A log, and one agent trace.
