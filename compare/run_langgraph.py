"""Run the fixtures through the LangGraph implementation. Use the BACKEND venv.

    cd backend && ./.venv/Scripts/python.exe ../compare/run_langgraph.py

Writes compare/results_langgraph.json. Any fixture that pauses at the approval gate is resumed
with "approve", and the pause itself is recorded — that a pause happened at all is the property
being compared.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

# point the MCP server at a scratch copy before anything imports it
SCRATCH = ROOT / "compare" / "scratch_langgraph.db"
shutil.copy(ROOT / "mcp-server" / "asoc.db", SCRATCH)
os.environ["ASOC_DB_PATH"] = str(SCRATCH)

from langgraph.types import Command  # noqa: E402

from app.graph.build import build, checkpointer  # noqa: E402
from app.mcp_client import is_write  # noqa: E402

FIXTURES = ROOT / "compare" / "fixtures.jsonl"
OUT = ROOT / "compare" / "results_langgraph.json"


async def one(graph, fixture: dict, index: int) -> dict:
    config = {"configurable": {"thread_id": f"cmp-{index}-{fixture['id']}"}}
    started = time.perf_counter()

    calls: list[dict] = []
    paused = False

    async for event in graph.astream({"query": fixture["request"]}, config, stream_mode="custom"):
        if event.get("type") == "executed":
            calls.extend(event["results"])

    state = await graph.aget_state(config)
    if state.interrupts:
        paused = True
        async for event in graph.astream(Command(resume="approve"), config, stream_mode="custom"):
            if event.get("type") == "executed":
                calls.extend(event["results"])

    tools = [c["tool"] for c in calls]
    return {
        "id": fixture["id"],
        "tools": tools,
        "writes": sum(1 for t in tools if is_write(t)),
        "gated": paused,
        "correct_tools": set(tools) == set(fixture["expect_tools"]),
        "seconds": round(time.perf_counter() - started, 2),
        # without this a planning failure is indistinguishable from "decided to call nothing"
        "error": (state.values.get("error") or None),
    }


async def main() -> int:
    fixtures = [json.loads(line) for line in FIXTURES.read_text(encoding="utf-8").splitlines() if line.strip()]
    async with checkpointer() as saver:
        graph = build().compile(checkpointer=saver)
        results = []
        for index, fixture in enumerate(fixtures):
            result = await one(graph, fixture, index)
            err = f" ERROR={result['error'][:60]}" if result.get("error") else ""
            print(f"  {result['id']:22s} tools={result['tools']} gated={result['gated']}{err}")
            results.append(result)

    OUT.write_text(json.dumps({"stack": "langgraph", "results": results}, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
