from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from langgraph.types import Command
from pydantic import BaseModel
from qdrant_client import QdrantClient

from app.config import settings
from app.graph.build import build, checkpointer

qdrant = QdrantClient(url=settings.qdrant_url)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """The checkpointer is held open for the process, not per request.

    A per-request connection would close between the interrupt and the approval that resumes it,
    which is exactly the state that has to survive.
    """
    async with checkpointer() as saver:
        app.state.graph = build().compile(checkpointer=saver)
        yield


app = FastAPI(title="ASOC", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    # any localhost port: the dev server moves when another project is already on 3000
    allow_origin_regex=r"http://localhost:\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None


class ApproveRequest(BaseModel):
    thread_id: str
    decision: str  # approve | reject


def sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, default=str)}\n\n"


async def run(graph, inputs, thread_id: str) -> AsyncIterator[str]:
    """Stream one graph run, then report whether it finished or stopped for approval."""
    config = {"configurable": {"thread_id": thread_id}}

    yield sse({"type": "thread", "thread_id": thread_id})
    try:
        async for event in graph.astream(inputs, config, stream_mode="custom"):
            yield sse(event)
    except Exception as exc:
        yield sse({"type": "error", "message": str(exc)})
        return

    state = await graph.aget_state(config)
    if state.interrupts:
        yield sse({"type": "awaiting_approval", "payload": state.interrupts[0].value})
    else:
        yield sse({"type": "done"})


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


@app.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    thread_id = req.thread_id or str(uuid.uuid4())
    return StreamingResponse(
        run(app.state.graph, {"query": req.message, "thread_id": thread_id}, thread_id),
        media_type="text/event-stream",
    )


@app.post("/approve")
async def approve(req: ApproveRequest) -> StreamingResponse:
    """Resume a conversation paused at the approval gate.

    The thread may have been paused by a different process — the checkpoint is on disk.
    """
    return StreamingResponse(
        run(app.state.graph, Command(resume=req.decision), req.thread_id),
        media_type="text/event-stream",
    )


@app.get("/thread/{thread_id}")
async def thread(thread_id: str):
    """What a conversation is currently waiting on. Lets a reloaded UI recover a pending approval."""
    state = await app.state.graph.aget_state({"configurable": {"thread_id": thread_id}})
    if not state.created_at:
        return JSONResponse(status_code=404, content={"error": "unknown thread"})
    return {
        "thread_id": thread_id,
        "next": list(state.next),
        "awaiting_approval": bool(state.interrupts),
        "pending": state.interrupts[0].value if state.interrupts else None,
        "answer": state.values.get("answer"),
    }
