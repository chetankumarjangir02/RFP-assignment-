"""Retrieval evaluation (spec §6.4): Recall@k + MRR + nDCG across search configs.

Compares vector-only vs hybrid vs hybrid+reranker on eval/questions.yaml and writes a
markdown report to eval/results/ (and prints it) for the README.

Run: python -m eval.run_eval
"""
from __future__ import annotations

import math
from datetime import date
from pathlib import Path

import yaml

from app.agents.retrieval_agent import retrieve

CONFIGS = ["vector", "hybrid", "hybrid_rerank"]
K_VALUES = [1, 3, 5, 10]
RETRIEVE_K = max(K_VALUES)


def _match(ev, spec: dict) -> bool:
    """True if a retrieved passage satisfies one expected spec (file/page/substring)."""
    m = ev.metadata
    if "file" in spec and spec["file"] != m.file_name:
        return False
    if "page" in spec and spec["page"] != m.page_number:
        return False
    sub = spec.get("must_contain")
    if sub and sub.lower() not in (ev.text or "").lower():
        return False
    # A spec with no constraints at all never matches (guards against empty specs).
    return any(k in spec for k in ("file", "page", "must_contain"))


def _first_hit_rank(ranked, expected: list[dict]) -> int | None:
    """1-based rank of the first retrieved passage matching ANY expected spec, else None."""
    for i, ev in enumerate(ranked, 1):
        if any(_match(ev, spec) for spec in expected):
            return i
    return None


def recall_at_k(rank: int | None, k: int) -> float:
    return 1.0 if (rank is not None and rank <= k) else 0.0


def reciprocal_rank(rank: int | None) -> float:
    return 1.0 / rank if rank else 0.0


def ndcg_at_k(rank: int | None, k: int) -> float:
    """Single relevant passage → nDCG@k reduces to 1/log2(rank+1) if within k, else 0."""
    if rank is None or rank > k:
        return 0.0
    return 1.0 / math.log2(rank + 1)


def run() -> str:
    questions = yaml.safe_load(Path("eval/questions.yaml").read_text())
    questions = [q for q in questions if q.get("expected")]

    rows: dict[str, dict] = {}
    per_question: dict[str, dict[str, int | None]] = {}

    print(f"Evaluating {len(questions)} questions x {len(CONFIGS)} configs "
          f"(local models load on first use)...", flush=True)
    for config in CONFIGS:
        print(f"  [{config}] ", end="", flush=True)
        recalls = {k: [] for k in K_VALUES}
        rrs: list[float] = []
        ndcgs = {k: [] for k in K_VALUES}
        for q in questions:
            # Measure the real agent retrieval path: query expansion + fusion + mode.
            ranked = retrieve(
                q["question"], bid_id=q.get("bid_id"), top_k=RETRIEVE_K, mode=config,
            )
            print(".", end="", flush=True)
            rank = _first_hit_rank(ranked, q["expected"])
            per_question.setdefault(q["id"], {})[config] = rank
            for k in K_VALUES:
                recalls[k].append(recall_at_k(rank, k))
                ndcgs[k].append(ndcg_at_k(rank, k))
            rrs.append(reciprocal_rank(rank))
        print(" done", flush=True)

        n = len(questions)
        rows[config] = {
            **{f"Recall@{k}": sum(recalls[k]) / n for k in K_VALUES},
            "MRR": sum(rrs) / n,
            **{f"nDCG@{k}": sum(ndcgs[k]) / n for k in K_VALUES},
        }

    report = _render(rows, per_question, len(questions))
    out_dir = Path("eval/results")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "retrieval_eval.md").write_text(report)
    print(report)
    return report


def _render(rows: dict, per_question: dict, n: int) -> str:
    lines = [
        "# Retrieval Evaluation Report",
        "",
        f"_Generated {date.today().isoformat()} · {n} questions across Bid1 + Bid2 · "
        f"measured on the agent retrieval path (query expansion + RRF fusion), "
        f"top-{RETRIEVE_K}, metadata-filtered by bid._",
        "",
        "## Summary (higher is better)",
        "",
        "| Config | Recall@1 | Recall@3 | Recall@5 | Recall@10 | MRR | nDCG@5 | nDCG@10 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for config in CONFIGS:
        r = rows[config]
        lines.append(
            f"| {config} | {r['Recall@1']:.3f} | {r['Recall@3']:.3f} | {r['Recall@5']:.3f} | "
            f"{r['Recall@10']:.3f} | {r['MRR']:.3f} | {r['nDCG@5']:.3f} | {r['nDCG@10']:.3f} |"
        )

    lines += ["", "## Per-question first-hit rank (— = not found in top-10)", "",
              "| # | " + " | ".join(CONFIGS) + " |",
              "|---|" + "|".join(["---"] * len(CONFIGS)) + "|"]
    for qid in sorted(per_question):
        cells = []
        for c in CONFIGS:
            rk = per_question[qid][c]
            cells.append(str(rk) if rk is not None else "—")
        lines.append(f"| {qid} | " + " | ".join(cells) + " |")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    run()
