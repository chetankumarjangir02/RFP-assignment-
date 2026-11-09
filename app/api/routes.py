"""REST endpoints (spec §6.3).

- POST /upload  : browser uploads a bid folder's files (multipart) -> saved + indexed
- POST /index   : index a folder already on the server (path-based; CLI/dev use)
- GET  /search  : standalone hybrid search
- POST /ask     : cited Q&A
- POST /extract  : full structured extraction for an (uploaded/indexed) bid

top_k and mode are optional with config defaults.
"""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, File, Form, Query, UploadFile
from pydantic import BaseModel

from app.agents.graph import run_extraction, run_qa
from app.agents.ingestion_agent import ingest
from app.models.evidence import Evidence
from app.search.engine import SearchEngine
from config.settings import settings

router = APIRouter()
_engine = SearchEngine()

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")
_ALLOWED_EXT = {".pdf", ".html", ".htm"}


def _safe_filename(name: str) -> str:
    """Strip any path components and unsafe characters (prevent path traversal)."""
    base = Path(name).name
    return _SAFE_NAME.sub("_", base) or "file"


def _bid_dir(bid_id: str) -> Path:
    safe = _SAFE_NAME.sub("_", bid_id) or "bid"
    return Path(settings.data_dir) / safe


class IndexRequest(BaseModel):
    bid_folder: str


class AskRequest(BaseModel):
    question: str
    bid_id: str | None = None


class ExtractRequest(BaseModel):
    bid_id: str
    bid_folder: str | None = None  # defaults to <data_dir>/<bid_id>


@router.post("/upload")
async def upload(
    bid_id: str = Form(...),
    files: list[UploadFile] = File(...),
) -> dict:
    """Receive uploaded bid-folder files, persist them under data/<bid_id>/, then index.

    The browser folder picker sends every file in the chosen directory; we keep the
    supported ones (.pdf/.html/.htm) and ignore the rest.
    """
    target = _bid_dir(bid_id)
    target.mkdir(parents=True, exist_ok=True)

    saved: list[str] = []
    skipped: list[str] = []
    for f in files:
        ext = Path(f.filename or "").suffix.lower()
        if ext not in _ALLOWED_EXT:
            skipped.append(f.filename or "")
            continue
        dest = target / _safe_filename(f.filename or "file")
        dest.write_bytes(await f.read())
        saved.append(dest.name)

    if not saved:
        return {"bid_id": bid_id, "saved": [], "skipped": skipped,
                "indexed_chunks": 0, "error": "No supported files (.pdf/.html) found."}

    indexed = ingest(str(target))
    return {
        "bid_id": bid_id,
        "folder": str(target),
        "saved": saved,
        "skipped": skipped,
        "indexed_chunks": indexed,
    }


@router.post("/index")
def index(req: IndexRequest) -> dict:
    """Parse + index a server-side bid folder (incremental). Path-based; for CLI/dev."""
    n = ingest(req.bid_folder)
    return {"indexed_chunks": n}


@router.get("/bids")
def bids() -> dict:
    """List the bid_ids currently indexed (drives the UI bid selector)."""
    return {"bids": _engine.list_bids()}


@router.get("/search")
def search(
    q: str,
    bid_id: str | None = None,
    doc_type: str | None = None,
    top_k: int | None = Query(default=None),
    mode: str | None = Query(default=None),
) -> list[Evidence]:
    """Standalone hybrid search. top_k / mode optional, default from config."""
    where: dict = {}
    if bid_id:
        # Tolerant match: 'bid 3' / 'Bid3' -> indexed 'bid_3'. Fall back to raw input.
        where["bid_id"] = _engine.resolve_bid(bid_id) or bid_id
    if doc_type:
        where["doc_type"] = doc_type
    return _engine.search(q, top_k=top_k, mode=mode, where=where or None)


@router.post("/ask")
def ask(req: AskRequest) -> dict:
    """Q&A mode: cited natural-language answer."""
    bid = req.bid_id
    if bid:
        resolved = _engine.resolve_bid(bid)
        if not resolved:
            avail = _engine.list_bids()
            msg = ", ".join(avail) if avail else "none indexed yet"
            return {
                "answer": f"'{bid}' is not an indexed bid. Available bids: {msg}.",
                "evidence": [],
            }
        bid = resolved
    answer, evidence = run_qa(req.question, bid)
    return {"answer": answer, "evidence": [e.model_dump() for e in evidence]}


@router.post("/extract")
def extract(req: ExtractRequest) -> dict:
    """Extraction mode: full structured BidRecord for an (uploaded/indexed) bid."""
    # Canonicalize so the state bid_id, folder name, and stored chunk bid_id all align.
    bid_id = _engine.resolve_bid(req.bid_id) or (_SAFE_NAME.sub("_", req.bid_id) or "bid")
    folder = req.bid_folder or str(_bid_dir(bid_id))
    record = run_extraction(bid_id, folder)
    return record.model_dump()
