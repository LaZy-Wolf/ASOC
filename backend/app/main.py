from fastapi import FastAPI
from fastapi.responses import JSONResponse
from qdrant_client import QdrantClient

from app.config import settings

app = FastAPI(title="ASOC")
qdrant = QdrantClient(url=settings.qdrant_url)


@app.get("/health")
def health():
    """Liveness + Qdrant reachability. 503 if the vector DB is down."""
    try:
        collections = [c.name for c in qdrant.get_collections().collections]
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "qdrant": {"reachable": False, "error": str(exc)}},
        )
    return {"status": "ok", "qdrant": {"reachable": True, "collections": collections}}
