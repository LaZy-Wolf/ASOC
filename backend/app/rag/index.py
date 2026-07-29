"""Offline corpus indexing. Run with `python -m app.rag.index`.

This is the ONLY place embeddings are computed. Nothing in the request path embeds anything —
that is the difference between a demo and a pipeline that stays under a latency budget.

One collection carries two named vectors: a dense one for semantics and a BM25 sparse one for
exact terms. Qdrant fuses them server-side, so there is no second index to keep in sync.
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastembed import SparseTextEmbedding, TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    Modifier,
    PointStruct,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

from app.config import ROOT, settings
from app.rag.chunk import Chunk, chunk_corpus

COLLECTION = "asoc"
DENSE_MODEL = "BAAI/bge-small-en-v1.5"
SPARSE_MODEL = "Qdrant/bm25"
DENSE_DIM = 384
CACHE_DIR = str(ROOT / "backend" / ".fastembed_cache")
CORPUS_DIR = ROOT / "data" / "corpus"


def dense_embedder() -> TextEmbedding:
    return TextEmbedding(model_name=DENSE_MODEL, cache_dir=CACHE_DIR)


def sparse_embedder() -> SparseTextEmbedding:
    return SparseTextEmbedding(model_name=SPARSE_MODEL, cache_dir=CACHE_DIR)


def payload(chunk: Chunk) -> dict:
    return {
        "chunk_id": chunk.id,
        "doc_id": chunk.doc_id,
        "heading_path": chunk.heading_path,
        "text": chunk.text,
        "doc_type": chunk.meta.get("doc_type", "unknown"),
        "department": chunk.meta.get("department", "unknown"),
        "source": chunk.meta.get("source", ""),
    }


def main() -> int:
    if not CORPUS_DIR.exists():
        print(f"corpus not found: {CORPUS_DIR}", file=sys.stderr)
        return 1

    chunks = chunk_corpus(CORPUS_DIR)
    docs = len({c.doc_id for c in chunks})
    print(f"chunked {docs} docs -> {len(chunks)} chunks")

    texts = [c.text for c in chunks]
    print(f"embedding dense ({DENSE_MODEL})...")
    dense = list(dense_embedder().embed(texts))
    print(f"embedding sparse ({SPARSE_MODEL})...")
    sparse = list(sparse_embedder().embed(texts))

    client = QdrantClient(url=settings.qdrant_url)
    if client.collection_exists(COLLECTION):
        client.delete_collection(COLLECTION)
    client.create_collection(
        COLLECTION,
        vectors_config={"dense": VectorParams(size=DENSE_DIM, distance=Distance.COSINE)},
        # IDF must be computed server-side: fastembed emits raw term frequencies, and
        # without this modifier every term would be weighted equally.
        sparse_vectors_config={"bm25": SparseVectorParams(modifier=Modifier.IDF)},
    )
    client.upsert(
        COLLECTION,
        points=[
            PointStruct(
                id=c.point_id,
                vector={
                    "dense": d.tolist(),
                    "bm25": SparseVector(indices=s.indices.tolist(), values=s.values.tolist()),
                },
                payload=payload(c),
            )
            for c, d, s in zip(chunks, dense, sparse)
        ],
    )

    count = client.count(COLLECTION).count
    print(f"indexed {count} points into '{COLLECTION}' (dense + bm25)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
