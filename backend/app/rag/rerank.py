"""Cross-encoder reranking.

Order matters: retrieve broadly first, then rerank the shortlist. Reranking the corpus is the
latency trap — a cross-encoder scores every (query, document) pair jointly, so cost is linear in
documents scored, unlike an embedding lookup.

Model chosen by measurement, not by size. ms-marco-MiniLM-L-6-v2 (80MB) was tried first on the
theory that a small ONNX model would be the sensible CPU default. On the golden set it was
dominated outright:

    hybrid + MiniLM,   25 candidates:  recall@5 0.907  MRR 0.773  p50 649ms
    hybrid + bge-base,  8 candidates:  recall@5 0.932  MRR 0.796  p50 1048ms

bge-reranker-base wins every quality metric at comparable latency, because the candidate count
is a far stronger latency lever than the model size. MiniLM also barely reordered anything —
against plain hybrid it improved 12 cases, degraded 12, and left 57 unchanged.
"""

from __future__ import annotations

from functools import lru_cache

from fastembed.rerank.cross_encoder import TextCrossEncoder

from app.rag.index import CACHE_DIR
from app.rag.retrieve import Hit

RERANK_MODEL = "BAAI/bge-reranker-base"


@lru_cache(maxsize=1)
def _encoder() -> TextCrossEncoder:
    return TextCrossEncoder(model_name=RERANK_MODEL, cache_dir=CACHE_DIR)


def rerank(query: str, hits: list[Hit], top_n: int = 5) -> list[Hit]:
    """Score each hit against the query and return the best top_n, highest first.

    Sets `rerank_score` on every returned hit. Scores are raw cross-encoder logits, so they are
    unbounded and not comparable across models — only their order and relative gaps mean anything.
    """
    if not hits:
        return []

    scores = list(_encoder().rerank(query, [h.text for h in hits]))
    for hit, score in zip(hits, scores):
        hit.rerank_score = float(score)

    return sorted(hits, key=lambda h: h.rerank_score, reverse=True)[:top_n]
