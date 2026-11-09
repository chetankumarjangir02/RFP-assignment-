# RFP Intelligence Platform — RAG Search Engine & Multi-Agent System

> **Submitted by Chetan Kumar Jangir · AI Engineer**

Ingests bid/RFP documents (HTML + PDF, incl. addendums), makes them searchable with a
**hybrid RAG engine**, and runs a **LangGraph multi-agent system** to (a) extract a
structured JSON record per bid with per-field citations + confidence, and (b) answer
free-form questions with citations. Generalizes to unseen bid folders with **no code
changes** (validated on a third, synthetic `bid_3`).

## Tech stack

| Layer | Choice |
|---|---|
| API | FastAPI + Uvicorn |
| Frontend | React + Vite + Tailwind (folder upload, search / ask / extract) |
| Orchestration | LangGraph |
| Schemas / config | Pydantic v2 + pydantic-settings |
| LLM | **Azure OpenAI GPT‑4** or **local Ollama** — swappable via `LLM_PROVIDER` |
| Embeddings | `BAAI/bge-base-en-v1.5` (sentence-transformers, local) |
| Vector store | Chroma (embedded, persistent, incremental upsert) |
| Keyword search | `rank-bm25` → fused with dense via Reciprocal Rank Fusion |
| Reranker | `BAAI/bge-reranker-base` cross-encoder |
| Parsing | PyMuPDF + pdfplumber (PDF), trafilatura + BeautifulSoup (HTML) |
| Observability | structlog — JSON per-agent step logs (input, tool calls, output, tokens, latency) |

Embeddings, BM25 and the reranker are **always local**; only the generative LLM calls a
provider. The JSON outputs and Q&A log in this repo were generated with **Azure OpenAI
GPT‑4** (`LLM_PROVIDER=azure_openai`); the same code runs fully offline on Ollama.

## Setup

> **Requires Python 3.10–3.12.** The ML stack (`chromadb` / `onnxruntime` / `torch`)
> does not yet publish wheels for Python 3.13+, so installing on a newer Python
> (e.g. 3.15) fails with `No matching distribution found for onnxruntime`. If your
> default `python3` is too new, call the interpreter explicitly — e.g. `python3.12`
> in place of `python` / `python3` in the commands below. Check with `python3 --version`.

Create and activate a virtual environment, then install dependencies.

**macOS / Linux:**

```bash
python3.12 -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt            # add requirements-dev.txt for tests
cp .env.example .env                        # then set your provider (see below)
```

**Windows (PowerShell):**

```powershell
py -3.12 -m venv .venv ; .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt            # add requirements-dev.txt for tests
copy .env.example .env                      # then set your provider (see below)
```

**Windows (Command Prompt):**

```cmd
py -3.12 -m venv .venv && .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

To leave the virtual environment later, run `deactivate` (same on all platforms).


**Choose an LLM provider in `.env`:**

```ini
# Option A — Azure OpenAI (what the committed outputs used)
LLM_PROVIDER=azure_openai
AZURE_OPENAI_GPT4_API_KEY=...
AZURE_OPENAI_GPT4_ENDPOINT=https://<resource>.openai.azure.com
AZURE_OPENAI_GPT4_DEPLOYMENT=<deployment-name>

# Option B — local, no keys
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen2.5:14b          # then: ollama pull qwen2.5:14b
```

No secrets live in code — all keys and model names come from env/`.env`.

## Run (one command per mode)

```bash
python main.py serve                        # FastAPI on :8000


python main.py index   --bid ./data/Bid1
python main.py extract --bid ./data/Bid1 --out ./outputs/Bid1.json
python main.py ask     --question "Is a bid bond required for Bid1, and how much?"


# or the whole app (UI + API + LLM) in one shot — see "Run with Docker" below:
docker compose up --build                   # UI on http://localhost:3000
```

REST (spec §6.3): `POST /index`, `GET /search?q=...&bid_id=...&top_k=5&mode=hybrid_rerank`,
`POST /ask`, `POST /extract`, `GET /bids`, `POST /upload`.
### Run with Docker (full app in one command)

The **entire application** — React UI, FastAPI API, and an Ollama LLM sidecar — comes up
together:

```bash
cp .env.example .env              # set LLM_PROVIDER (see below); first time only
docker compose up --build         # later just: docker compose up
```

**Open the app here:**

| URL | What |
|---|---|
| **http://localhost:3000** | the full **Web UI** (Upload · Search · Ask · Extract) |
| http://localhost:8000/docs | API Swagger UI (optional — try endpoints directly) |
| http://localhost:8000/health | liveness check |

Three services start: **frontend (UI) on `:3000`**, **API on `:8000`**, and an **Ollama
sidecar on `:11434`**. The UI proxies its `/api/*` calls to the API automatically (no CORS
setup). Your `./data`, `./storage` (index) and `./outputs` are mounted into the API
container, so the bids and existing index are already available.

**Pick the LLM provider in `.env` before `up`:**

```bash
# Fully local, no keys (matches the bundled Ollama sidecar):
#   LLM_PROVIDER=ollama   — then, once the stack is up, pull the model once:
docker compose exec ollama ollama pull qwen2.5:14b

# Or Azure (what the committed outputs used): set LLM_PROVIDER=azure_openai + AZURE_* in .env
```

Your `.env` is read at runtime via `env_file` and is **not** baked into the image
(`.dockerignore` excludes it), so keys never ship inside a built image.

Note: the **first** `/search` or `/extract` call downloads the local embedding + reranker
models inside the API container (one-time, slow).

### Web UI (React + Vite + Tailwind) — local dev only

Docker already serves the UI on `:3000`. For hot-reload development *without* Docker, run
the backend (`python main.py serve`) and, in a second terminal:

```bash
cd frontend && npm install && npm run dev   # http://localhost:5173
```

Upload a bid **folder** (browser folder picker) → it is saved server-side under
`data/<bid_id>/` and indexed. The uploaded bid becomes the active context for every tab
automatically — Search, Ask and Extract all scope to it (no bid id to re-type).

## Design decisions

- **Chunking — paragraph/table-aware, `CHUNK_SIZE=800`, `CHUNK_OVERLAP=150` (chars).**
  RFP facts are short and local (a due date, a part number), so 800‑char windows keep a
  fact with its surrounding context without diluting embeddings; 150‑char overlap stops a
  value from being split across a boundary. **Tables are emitted as their own chunks**
  (`is_table=True`) because spec/bid tables carry model numbers and requirements that line
  wrapping would scramble. One `Document` per PDF page keeps `page_number` exact for
  citations.
- **Embeddings — `bge-base-en-v1.5`.** Strong retrieval quality for its size, runs locally
  (no embedding API cost / data egress), 768‑dim fits Chroma comfortably.
- **Hybrid retrieval — dense (bge) + BM25, fused with RRF, then cross-encoder rerank.**
  Dense search handles paraphrase ("deadline" ≈ "due date"); BM25 nails exact tokens
  (`WD22TB4`, `JA-207652`) that dense search blurs. RRF needs no score calibration between
  the two. Mode is configurable (`vector | keyword | hybrid | hybrid_rerank`); `top_k` is
  per-request. See the evaluation below for why rerank is the default.
- **Metadata filtering.** Every chunk carries `bid_id`, `file_name`, `doc_type`,
  `addendum_number`, `page_number`, `document_date` — enabling "only Bid2 specs" scoping,
  addendum reconciliation, and traceable citations.
- **Query expansion.** The retrieval agent expands queries (e.g. "deadline" → "due date,
  submission deadline, closing date") and fuses the variants' results.
- **Agent framework — LangGraph.** Chosen over CrewAI/AutoGen because extraction is a
  **stateful graph with a feedback loop**, not a linear chain: the Validator→Orchestrator
  edge re-runs retrieval/extraction for rejected fields with a **bounded retry count**
  (`MAX_VALIDATION_RETRIES`), which LangGraph's conditional edges + shared `GraphState`
  express directly. Field groups extract **concurrently** (ThreadPoolExecutor). All
  agent-to-agent messages are Pydantic models.
- **Prompts & structured outputs.** Agents never receive whole documents — only retrieved,
  cited passages, under a strict system prompt: *"use ONLY the evidence; if it isn't there,
  return null; never guess."* Every LLM call requests **JSON matching a Pydantic schema**
  (`complete_structured`) with a one-shot repair retry on invalid JSON, so agent-to-agent
  messages are typed, not free text. Ambiguous fields get a short per-field **definition**
  (e.g. Bid Number = "the solicitation/PORFP id, not an internal project number") rather
  than hard-coded values, which keeps extraction generalizable while disambiguating intent.
  The Bid Summary field uses a dedicated "summarize the retrieved overview passages" prompt
  instead of a lookup.
- **Guardrails.** Every non-null value must carry ≥1 citation (Validator rejects otherwise);
  missing facts return `null` + "Not found in documents" — never guessed, with absence
  confidence capped. Errors (LLM timeout, bad JSON, empty retrieval) degrade to a safe
  not-found instead of crashing.

## Evaluation (spec §6.4)

18 question→expected-passage pairs across both bids in [`eval/questions.yaml`](eval/questions.yaml),
scored on Recall@k, MRR and nDCG for three configs. Full report:
[`eval/results/retrieval_eval.md`](eval/results/retrieval_eval.md).

```bash
python -m eval.run_eval
```

| Config | Recall@1 | Recall@3 | Recall@5 | Recall@10 | MRR | nDCG@10 |
|---|---|---|---|---|---|---|
| vector | 0.333 | 0.611 | 0.778 | 0.833 | 0.488 | 0.571 |
| hybrid | 0.333 | 0.556 | 0.722 | 0.833 | 0.486 | 0.570 |
| **hybrid_rerank** | **0.556** | **0.667** | 0.667 | **0.889** | **0.630** | **0.688** |

_Measured on the real agent retrieval path (query expansion + RRF fusion) via
`retrieve()`, so the numbers reflect what the agents actually see._

**Reading it:** the cross-encoder reranker wins across the board — **Recall@1 0.333 → 0.556,
MRR 0.49 → 0.63, and the best Recall@10 (0.889)** — because it reranks a *fused, expanded*
candidate pool once, so the right passage both lands at the top more often and is kept in
range more often. That top-rank quality is exactly what the extraction/QA agents consume,
so `hybrid_rerank` is the default. Three questions (procurement contact, issuing org,
agency POC) still miss in all configs — a genuine weakness: that information sits in dense
contact blocks the query embeddings rank poorly, which is why the extraction agent
additionally biases those fields toward the `bid_page` header.

## Deliverables

| Deliverable | Location |
|---|---|
| Per-bid JSON outputs | [`outputs/Bid1.json`](outputs/Bid1.json), [`outputs/Bid2.json`](outputs/Bid2.json) |
| Retrieval eval report | [`eval/results/retrieval_eval.md`](eval/results/retrieval_eval.md) |
| Sample Q&A log (12 cited) | [`docs/qa_log.md`](docs/qa_log.md) |
| Agent trace (Bid1 extraction) | [`outputs/traces/Bid1_extraction_trace.jsonl`](outputs/traces/Bid1_extraction_trace.jsonl) |
| Architecture diagram | [`docs/architecture.md`](docs/architecture.md) |

**Extraction results:** Bid1 = 16 passed / 0 failed / 4 not_found (Due Date correctly
reconciled to July 9, 2024 from Addendum 2); Bid2 = 15 passed / 1 failed / 4 not_found.
Not-found fields are genuinely absent or vendor-proposed (e.g. Part_no, Bid Bond), returned
as `null` with a reason rather than guessed.

## Tests

```bash
pip install -r requirements-dev.txt
pytest                                       # 31 tests: parsing, metadata, cleaner, BM25, fusion, models
```

Covers the two spec-mandated components: **parsing** (PDF page extraction, doc_type /
addendum / date inference, hyphenation & header-stripping) and **search** (BM25 exact-token
ranking, metadata filtering, RRF fusion). All tests are local — no LLM or network.

## Project layout

```
app/{models,ingestion,search,agents,api,observability}/   config/   eval/   tests/
data/ (inputs)   storage/ (index)   outputs/ (JSON + traces)   docs/   frontend/
```

## Assumptions & known limitations

- **QA mode vs Extraction mode on addendums.** Extraction mode runs a dedicated Addendum
  Reconciliation agent, so the extracted `Due Date` correctly reflects Addendum 2
  (July 9, 2024). The lighter **QA path** (retrieve → answer) does *not* run that
  reconciliation, so an addendum-override question can surface the original date if
  retrieval ranks it higher (see Q1 in the Q&A log). Extraction output is the source of
  truth for reconciled fields.
- **Contact / issuing-organization retrieval is the weakest area** (see eval misses);
  extraction compensates with a `bid_page` doc_type bias, but pure search can miss them.
- **Local (Ollama) vs Azure** trade accuracy for cost/offline operation; committed outputs
  used Azure GPT‑4.
- `data/bid_3` is a small **synthetic** folder used to demonstrate unseen-bid
  generalization, not a provided bid.
- OCR for scanned pages is not implemented (bonus); unreadable/empty pages are logged and
  skipped rather than OCR'd.
