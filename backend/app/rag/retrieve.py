"""Dense top-k retrieval.

P1 baseline. P3 replaces this with hybrid dense+sparse RRF fusion plus reranking, and this
function stays as the measured baseline in the eval table.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from fastembed import TextEmbedding
from qdrant_client import QdrantClient

from app.config import settings
from app.rag.index import CACHE_DIR, COLLECTION, DENSE_MODEL


@dataclass
class Hit:
    chunk_id: str
    doc_id: str
    heading_path: str
    text: str
    doc_type: str
    source: str
    score: float


@lru_cache(maxsize=1)
def _embedder() -> TextEmbedding:
    """Loaded once per process — model init is seconds, embedding a query is milliseconds."""
    return TextEmbedding(model_name=DENSE_MODEL, cache_dir=CACHE_DIR)


@lru_cache(maxsize=1)
def _client() -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url)


def retrieve(query: str, top_k: int = 5) -> list[Hit]:
    vector = next(iter(_embedder().query_embed(query))).tolist()
    result = _client().query_points(
        COLLECTION, query=vector, using="dense", limit=top_k, with_payload=True
    )
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
        for p in result.points
    ]
