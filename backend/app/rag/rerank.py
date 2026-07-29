"""Cross-encoder reranking.

Order matters: retrieve broadly first, then rerank the shortlist. Reranking the corpus is the
latency trap — a cross-encoder scores every (query, document) pair jointly, so cost is linear in
documents scored, unlike an embedding lookup.

ms-marco-MiniLM-L-6-v2 (80MB ONNX) over bge-reranker-base (1.04GB): 13x smaller and much faster
on CPU. Whether that costs accuracy is a question the eval harness answers, not a guess.
"""

from __future__ import annotations

from functools import lru_cache

from fastembed.rerank.cross_encoder import TextCrossEncoder

from app.rag.index import CACHE_DIR
from app.rag.retrieve import Hit

RERANK_MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"


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
