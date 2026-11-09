# Architecture

Two views of the same system: a Mermaid flow (renders on GitHub) and an ASCII reference.

## Flow (Mermaid)

```mermaid
flowchart TB
    subgraph ING["Ingestion & Parsing (Part A)"]
        FILES["HTML / PDF files"] --> LOADER["loader → pdf_parser / html_parser"]
        LOADER --> CLEAN["cleaner + metadata"]
        CLEAN --> CHUNK["chunker (paragraph/table-aware, +overlap)"]
    end

    CHUNK -->|chunks + metadata| ENGINE

    subgraph ENGINE["Search Engine (Part B) — single grounding layer"]
        EMB["bge embeddings → Chroma (dense)"]
        BM25["BM25 (keyword)"]
        EMB & BM25 --> RRF["RRF fusion"]
        RRF --> RERANK["cross-encoder rerank"]
    end

    subgraph AGENTS["Multi-Agent System (Part C) — LangGraph"]
        ORCH["Orchestrator / Planner<br/>(plan, route, bounded retries)"]
        RET["Retrieval agent<br/>(rewrite/expand → search tool)"]
        EXT["Extraction agents<br/>(field groups, parallel)"]
        REC["Addendum Reconciliation"]
        VAL["Validator / Critic"]
        QA["Q&A / Report agent"]
        ORCH --> RET --> EXT --> REC --> VAL
        VAL -->|failed field, retries left| EXT
        ORCH --> QA
    end

    RET -.->|search()| ENGINE
    QA -.->|search()| ENGINE
    USER["User goal / question"] --> ORCH
    VAL -->|passed / retries exhausted| OUT["Structured JSON (cited) / Cited answer"]
    QA --> OUT

    STATE["Shared GraphState: plan · evidence · draft fields · validation · output"]
    STATE -.-> AGENTS
```

## Reference (ASCII)

```
            ┌──────────────────────────────────────────────────────────┐
            │                     Ingestion (Part A)                    │
  HTML/PDF ─┤ loader → pdf_parser / html_parser → cleaner → metadata   │
            │         → chunker (heading/table-aware, +overlap)         │
            └───────────────────────────┬──────────────────────────────┘
                                         │ Chunks (+ metadata)
                                         ▼
            ┌──────────────────────────────────────────────────────────┐
            │              Search Engine (Part B) — engine.py           │
            │  embedder → Chroma (dense)   BM25 (keyword)               │
            │              └──── RRF fusion ────┘ → reranker            │
            │  modes: vector | keyword | hybrid | hybrid_rerank         │
            └───────────────┬───────────────────────┬──────────────────┘
                            │ search() tool         │ REST: /index /search /ask /extract
                            ▼                        ▼
            ┌──────────────────────────────────────────────────────────┐
            │          Multi-Agent System (Part C) — LangGraph          │
            │  Orchestrator ─ plan/route/retry (bounded)                │
            │    ├─ Ingestion agent                                     │
            │    ├─ Retrieval agent ──(calls search engine)            │
            │    ├─ Extraction agents (field groups, parallel)         │
            │    ├─ Addendum Reconciliation agent                      │
            │    ├─ Validator/Critic ──(failed → re-extract loop)      │
            │    └─ Q&A / Report agent                                 │
            │  Shared state: plan, evidence, draft fields, validation   │
            └───────────────────────────┬──────────────────────────────┘
                                         ▼
                 Structured JSON (per bid, cited) / Cited answers
```

See `CLAUDE.md` for the invariants (single grounding layer, metadata-on-every-chunk,
shared state + bounded feedback loop) and `README.md` for design-decision rationale.
