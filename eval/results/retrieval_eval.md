# Retrieval Evaluation Report

_Generated 2026-11-09 · 18 questions across Bid1 + Bid2 · measured on the agent retrieval path (query expansion + RRF fusion), top-10, metadata-filtered by bid._

## Summary (higher is better)

| Config | Recall@1 | Recall@3 | Recall@5 | Recall@10 | MRR | nDCG@5 | nDCG@10 |
|---|---|---|---|---|---|---|---|
| vector | 0.333 | 0.611 | 0.778 | 0.833 | 0.488 | 0.554 | 0.571 |
| hybrid | 0.333 | 0.556 | 0.722 | 0.833 | 0.486 | 0.531 | 0.570 |
| hybrid_rerank | 0.556 | 0.667 | 0.667 | 0.889 | 0.630 | 0.618 | 0.688 |

## Per-question first-hit rank (— = not found in top-10)

| # | vector | hybrid | hybrid_rerank |
|---|---|---|---|
| q01 | 2 | 6 | 1 |
| q02 | 5 | 4 | 3 |
| q03 | 1 | 1 | 1 |
| q04 | 1 | 3 | 1 |
| q05 | — | — | — |
| q06 | 1 | 1 | 1 |
| q07 | — | — | — |
| q08 | 1 | 1 | 6 |
| q09 | 1 | 1 | 1 |
| q10 | 3 | 3 | 2 |
| q11 | 1 | 1 | 1 |
| q12 | 4 | 2 | 1 |
| q13 | 3 | 4 | 1 |
| q14 | 2 | 1 | 1 |
| q15 | 5 | 4 | 9 |
| q16 | — | — | 10 |
| q17 | 3 | 2 | 8 |
| q18 | 8 | 6 | 1 |
