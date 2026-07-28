"""Offline corpus indexing. Run with `python -m app.rag.index`.

This is the ONLY place embeddings are computed. Nothing in the request path embeds anything —
that is the difference between a demo and a pipeline that stays under a latency budget.
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.config import ROOT, settings
from app.rag.chunk import Chunk, chunk_corpus

COLLECTION = "asoc"
DENSE_MODEL = "BAAI/bge-small-en-v1.5"
DENSE_DIM = 384
CACHE_DIR = str(ROOT / "backend" / ".fastembed_cache")
CORPUS_DIR = ROOT / "data" / "corpus"


def embedder() -> TextEmbedding:
    return TextEmbedding(model_name=DENSE_MODEL, cache_dir=CACHE_DIR)


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

    print(f"embedding with {DENSE_MODEL} (first run downloads the model)...")
    vectors = list(embedder().embed([c.text for c in chunks]))

    client = QdrantClient(url=settings.qdrant_url)
    if client.collection_exists(COLLECTION):
        client.delete_collection(COLLECTION)
    client.create_collection(
        COLLECTION,
        vectors_config={"dense": VectorParams(size=DENSE_DIM, distance=Distance.COSINE)},
    )
    client.upsert(
        COLLECTION,
        points=[
            PointStruct(id=c.point_id, vector={"dense": v.tolist()}, payload=payload(c))
            for c, v in zip(chunks, vectors)
        ],
    )

    count = client.count(COLLECTION).count
    print(f"indexed {count} points into '{COLLECTION}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
