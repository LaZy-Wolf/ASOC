"""Retrieval: a dense baseline and a hybrid path.

`dense_retrieve` is kept deliberately — it is the baseline the eval table measures against,
not dead code.

`hybrid_retrieve` prefetches dense and BM25 candidates and lets Qdrant fuse them with
Reciprocal Rank Fusion server-side. RRF scores a document by sum(1 / (k + rank_i)) across the
rankings it appears in, with k=60. The constant damps the influence of the very top ranks, so a
document ranked 1st by one retriever and 40th by the other does not automatically beat one
ranked 3rd by both. See tests/test_rrf.py for the formula worked by hand.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from fastembed import SparseTextEmbedding, TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    Fusion,
    FusionQuery,
    MatchValue,
    Prefetch,
    SparseVector,
)

from app.config import settings
from app.rag.index import CACHE_DIR, COLLECTION, DENSE_MODEL, SPARSE_MODEL

CANDIDATES = 25  # per retriever, before fusion


@dataclass
class Hit:
    chunk_id: str
    doc_id: str
    heading_path: str
    text: str
    doc_type: str
    source: str
    score: float
    rerank_score: float | None = field(default=None)


@lru_cache(maxsize=1)
def _dense() -> TextEmbedding:
    """Loaded once per process — init is seconds, embedding a query is milliseconds."""
    return TextEmbedding(model_name=DENSE_MODEL, cache_dir=CACHE_DIR)


@lru_cache(maxsize=1)
def _sparse() -> SparseTextEmbedding:
    return SparseTextEmbedding(model_name=SPARSE_MODEL, cache_dir=CACHE_DIR)


@lru_cache(maxsize=1)
def _client() -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url)


def _to_hits(points) -> list[Hit]:
    return [
        Hit(
            chunk_id=p.payload["chunk_id"],
            doc_id=p.payload["doc_id"],
            heading_path=p.payload["heading_path"],
            text=p.payload["text"],
            doc_type=p.payload["doc_type"],
            source=p.payload["source"],
            score=p.score,
        )
        for p in points
    ]


def _filter(doc_type: str | None) -> Filter | None:
    if not doc_type:
        return None
    return Filter(must=[FieldCondition(key="doc_type", match=MatchValue(value=doc_type))])


def dense_retrieve(query: str, top_k: int = 5, doc_type: str | None = None) -> list[Hit]:
    """Dense top-k. The P1 baseline, retained as the eval's control."""
    vector = next(iter(_dense().query_embed(query))).tolist()
    result = _client().query_points(
        COLLECTION,
        query=vector,
        using="dense",
        limit=top_k,
        query_filter=_filter(doc_type),
        with_payload=True,
    )
    return _to_hits(result.points)


def hybrid_retrieve(query: str, top_k: int = CANDIDATES, doc_type: str | None = None) -> list[Hit]:
    """Dense + BM25 candidates fused with RRF inside Qdrant."""
    dense_vec = next(iter(_dense().query_embed(query))).tolist()
    sparse_raw = next(iter(_sparse().query_embed(query)))
    sparse_vec = SparseVector(
        indices=sparse_raw.indices.tolist(), values=sparse_raw.values.tolist()
    )
    where = _filter(doc_type)

    result = _client().query_points(
        COLLECTION,
        prefetch=[
            Prefetch(query=dense_vec, using="dense", limit=CANDIDATES, filter=where),
            Prefetch(query=sparse_vec, using="bm25", limit=CANDIDATES, filter=where),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=top_k,
        with_payload=True,
    )
    return _to_hits(result.points)
