"""Retrieval evaluation. Run with `python -m eval.retrieval_eval`.

Deterministic and LLM-free on purpose: recall, MRR and nDCG are computed from rank positions, so
the numbers are reproducible, cost nothing, and do not drift with a judge model's mood. Answer-level
judgement (faithfulness) is a separate, smaller job — see ragas_subset.py.

Gold labels are (doc_id, heading substring) pairs rather than chunk ids, so re-chunking does not
silently invalidate the set.
"""

from __future__ import annotations

import json
import math
import statistics
import time
from dataclasses import dataclass
from pathlib import Path

from app.rag.rerank import rerank
from app.rag.retrieve import Hit, dense_retrieve, hybrid_retrieve
from app.rag.route import CONFIDENCE_THRESHOLD

HERE = Path(__file__).resolve().parent
GOLDEN = HERE / "golden_set.jsonl"
RESULTS = HERE / "RESULTS.md"
K = 5


@dataclass
class Case:
    q: str
    type: str
    gold: list[list[str]]


def load_cases() -> list[Case]:
    with GOLDEN.open(encoding="utf-8") as fh:
        return [Case(**json.loads(line)) for line in fh if line.strip()]


def matches(hit: Hit, gold: list[str]) -> bool:
    doc, heading = gold
    return hit.doc_id == doc and heading.lower() in hit.heading_path.lower()


def score_case(case: Case, hits: list[Hit]) -> tuple[float, float, float]:
    """Returns (recall@K, reciprocal rank, nDCG@K) for one answerable case."""
    top = hits[:K]

    found = sum(1 for gold in case.gold if any(matches(h, gold) for h in top))
    recall = found / len(case.gold)

    rr = 0.0
    for rank, hit in enumerate(top, 1):
        if any(matches(hit, gold) for gold in case.gold):
            rr = 1 / rank
            break

    dcg = sum(
        1 / math.log2(rank + 1)
        for rank, hit in enumerate(top, 1)
        if any(matches(hit, gold) for gold in case.gold)
    )
    ideal = sum(1 / math.log2(rank + 1) for rank in range(1, min(len(case.gold), K) + 1))
    ndcg = dcg / ideal if ideal else 0.0

    return recall, rr, ndcg


def run_config(name: str, retrieve, cases: list[Case], scored: bool) -> dict:
    recalls, rrs, ndcgs, latencies = [], [], [], []
    refusals_on_unanswerable = 0
    refusals_on_answerable = 0

    for case in cases:
        started = time.perf_counter()
        hits = retrieve(case.q)
        latencies.append((time.perf_counter() - started) * 1000)

        # a config with calibrated scores can decline to answer; the others cannot
        refused = scored and (not hits or hits[0].rerank_score < CONFIDENCE_THRESHOLD)

        if case.type == "unanswerable":
            refusals_on_unanswerable += refused
            continue

        if refused:
            refusals_on_answerable += 1
        recall, rr, ndcg = score_case(case, hits)
        recalls.append(recall)
        rrs.append(rr)
        ndcgs.append(ndcg)

    unanswerable = sum(1 for c in cases if c.type == "unanswerable")
    answerable = len(cases) - unanswerable

    return {
        "name": name,
        "recall": statistics.mean(recalls),
        "mrr": statistics.mean(rrs),
        "ndcg": statistics.mean(ndcgs),
        "p50": statistics.median(latencies),
        "p95": sorted(latencies)[int(len(latencies) * 0.95) - 1],
        "refusal": (refusals_on_unanswerable / unanswerable) if scored else None,
        "false_refusal": (refusals_on_answerable / answerable) if scored else None,
    }


def cell(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def threshold_curve(cases: list[Case]) -> tuple[list[tuple[float, float, float]], dict]:
    """Refusal recall vs false refusal across candidate thresholds, plus signal separability.

    Also records the top-1 score range of each retriever, which is what decides whether a signal
    can carry a confidence gate at all.
    """
    rerank_ans, rerank_unans = [], []
    rrf_ans, rrf_unans = [], []

    for case in cases:
        fused = hybrid_retrieve(case.q)
        top = rerank(case.q, list(fused), top_n=1)[0]
        unanswerable = case.type == "unanswerable"
        (rerank_unans if unanswerable else rerank_ans).append(top.rerank_score)
        (rrf_unans if unanswerable else rrf_ans).append(fused[0].score)

    curve = [
        (
            t / 2,
            sum(1 for s in rerank_unans if s < t / 2) / len(rerank_unans),
            sum(1 for s in rerank_ans if s < t / 2) / len(rerank_ans),
        )
        for t in range(-16, -5)
    ]
    ranges = {
        "rerank": (min(rerank_ans), max(rerank_ans), min(rerank_unans), max(rerank_unans)),
        "rrf": (min(rrf_ans), max(rrf_ans), min(rrf_unans), max(rrf_unans)),
    }
    return curve, ranges


def render(rows: list[dict], cases: list[Case], curve, ranges) -> str:
    unanswerable = sum(1 for c in cases if c.type == "unanswerable")
    multi_hop = sum(1 for c in cases if c.type == "multi_hop")
    baseline, best = rows[0], rows[-1]

    lines = [
        "# Retrieval evaluation",
        "",
        f"{len(cases)} questions: {len(cases) - unanswerable} answerable "
        f"({multi_hop} multi-hop), {unanswerable} deliberately unanswerable.",
        "",
        f"Generated by `python -m eval.retrieval_eval`. k={K}.",
        "",
        "| config | recall@5 | MRR | nDCG@5 | refusal recall | false refusal | p50 ms | p95 ms |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['name']} | {row['recall']:.3f} | {row['mrr']:.3f} | {row['ndcg']:.3f} "
            f"| {cell(row['refusal'])} | {cell(row['false_refusal'])} "
            f"| {row['p50']:.0f} | {row['p95']:.0f} |"
        )

    fusion = rows[1]
    delta_recall = best["recall"] - baseline["recall"]
    delta_mrr = best["mrr"] - baseline["mrr"]
    fusion_share = (fusion["recall"] - baseline["recall"]) / delta_recall if delta_recall else 0.0
    slowdown = best["p50"] / baseline["p50"] if baseline["p50"] else 0.0

    lines += [
        "",
        "## Reading this",
        "",
        f"- **recall@5 {baseline['recall']:.3f} -> {best['recall']:.3f}** "
        f"({delta_recall:+.3f}) from the dense baseline to hybrid + rerank.",
        f"- **MRR {baseline['mrr']:.3f} -> {best['mrr']:.3f}** ({delta_mrr:+.3f}).",
        f"- Fusion accounts for {fusion_share:.0%} of the recall gain and costs nothing "
        f"({baseline['p50']:.0f}ms -> {fusion['p50']:.0f}ms). Reranking supplies the remaining "
        f"{1 - fusion_share:.0%} and is {slowdown:.0f}x slower than the baseline. If latency ever "
        "matters more than the last few points of recall, dropping the reranker is the obvious "
        "lever — at the cost of the refusal gate, for the reason below.",
        "- **refusal recall** is the share of unanswerable questions correctly declined. Only the "
        "reranked config has a calibrated score to threshold on, so the others report n/a rather "
        "than a number derived from an arbitrary cutoff.",
        "- **false refusal** is the share of answerable questions wrongly declined. It is the cost "
        "side of the refusal threshold and must be read alongside it.",
        "- Latency is wall clock per query on CPU, including query embedding.",
        "",
        "Gold labels are (document, heading substring) pairs, so re-chunking does not silently "
        "invalidate the set.",
        "",
        "## Why rerank at all, when fusion is free",
        "",
        "Reranking buys real but modest recall for a large latency bill. Its second job is what "
        "makes it non-optional here: it is the only stage that produces an **absolute** relevance "
        "score. RRF scores a "
        "document from its rank positions, so the top result scores about the same whether the "
        "corpus answers the question or not — the top-1 ranges below overlap completely, and an "
        "unanswerable question can reach the maximum score. Without a cross-encoder there is no "
        "signal to threshold, and the refusal gate cannot exist.",
        "",
        "| signal | answerable top-1 | unanswerable top-1 | usable as a confidence gate |",
        "|---|---|---|---|",
        f"| RRF (hybrid) | {ranges['rrf'][0]:.3f} .. {ranges['rrf'][1]:.3f} "
        f"| {ranges['rrf'][2]:.3f} .. {ranges['rrf'][3]:.3f} | no |",
        f"| cross-encoder | {ranges['rerank'][0]:+.3f} .. {ranges['rerank'][1]:+.3f} "
        f"| {ranges['rerank'][2]:+.3f} .. {ranges['rerank'][3]:+.3f} | yes, with a chosen "
        "operating point |",
        "",
        "## Choosing the refusal threshold",
        "",
        "The two distributions overlap, so no threshold gives perfect refusal at zero false "
        "refusal. This is the operating curve:",
        "",
        "| threshold | refusal recall | false refusal |",
        "|---|---|---|",
        *[f"| {t:+.1f} | {rr:.3f} | {fr:.3f} |" for t, rr, fr in curve],
        "",
        f"Shipping **{CONFIDENCE_THRESHOLD:+.1f}**. The errors are not symmetric: a false refusal "
        "costs an unnecessary \"I don't know\"; a missed refusal invites the model to invent an "
        "access or security policy. The second is worse, so the operating point leans toward "
        "refusing.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    cases = load_cases()
    print(f"{len(cases)} cases loaded")

    configs = [
        ("dense top-k (baseline)", lambda q: dense_retrieve(q, top_k=K), False),
        ("hybrid RRF", lambda q: hybrid_retrieve(q, top_k=K), False),
        ("hybrid + rerank", lambda q: rerank(q, hybrid_retrieve(q), top_n=K), True),
    ]

    rows = []
    for name, fn, scored in configs:
        print(f"  running {name}...")
        rows.append(run_config(name, fn, cases, scored))

    print("  sweeping refusal threshold...")
    curve, ranges = threshold_curve(cases)

    RESULTS.write_text(render(rows, cases, curve, ranges), encoding="utf-8")
    print(f"\nwrote {RESULTS}\n")
    for row in rows:
        print(
            f"  {row['name']:26s} recall@5={row['recall']:.3f}  MRR={row['mrr']:.3f}  "
            f"nDCG={row['ndcg']:.3f}  p50={row['p50']:.0f}ms"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
