"""CLI entrypoint (spec §9: runnable with one command).

Examples:
    python main.py index   --bid ./data/Bid1
    python main.py extract --bid ./data/Bid1 --out ./outputs/Bid1.json
    python main.py ask     --question "Is a bid bond required for Bid1?"
    python main.py serve
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _bid_id(folder: str) -> str:
    return Path(folder).name


def cmd_index(args: argparse.Namespace) -> None:
    from app.agents.ingestion_agent import ingest

    n = ingest(args.bid)
    print(f"Indexed {n} chunks from {args.bid}")


def cmd_extract(args: argparse.Namespace) -> None:
    from app.agents.graph import run_extraction

    record = run_extraction(_bid_id(args.bid), args.bid)
    out = args.out or f"./outputs/{_bid_id(args.bid)}.json"
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(record.model_dump(), indent=2))
    print(f"Wrote {out}")


def cmd_ask(args: argparse.Namespace) -> None:
    from app.agents.graph import run_qa

    answer, evidence = run_qa(args.question, args.bid_id)
    print(answer)
    for e in evidence:
        print(f"  - {e.metadata.file_name} p.{e.metadata.page_number}")


def cmd_serve(args: argparse.Namespace) -> None:
    import uvicorn

    uvicorn.run("app.api.server:app", host=args.host, port=args.port, reload=args.reload)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="RFP Intelligence Platform")
    sub = p.add_subparsers(dest="command", required=True)

    pi = sub.add_parser("index", help="Parse + index a bid folder")
    pi.add_argument("--bid", required=True)
    pi.set_defaults(func=cmd_index)

    pe = sub.add_parser("extract", help="Extract structured JSON for a bid folder")
    pe.add_argument("--bid", required=True)
    pe.add_argument("--out", default=None)
    pe.set_defaults(func=cmd_extract)

    pa = sub.add_parser("ask", help="Ask a question across indexed bids")
    pa.add_argument("--question", required=True)
    pa.add_argument("--bid-id", default=None, dest="bid_id")
    pa.set_defaults(func=cmd_ask)

    ps = sub.add_parser("serve", help="Run the FastAPI server")
    ps.add_argument("--host", default="0.0.0.0")
    ps.add_argument("--port", type=int, default=8000)
    ps.add_argument("--reload", action="store_true")
    ps.set_defaults(func=cmd_serve)

    return p


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
