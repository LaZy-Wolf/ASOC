"""Render compare/NOTES.md from both stacks' results. Stdlib only, runs in either venv.

    python render_notes.py

The per-fixture table is generated. The capability matrix is authored, because those rows are
judgements — each one cites the evidence it rests on rather than asserting a winner.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures.jsonl"
OUT = HERE / "NOTES.md"


def load(stack: str) -> dict:
    path = HERE / f"results_{stack}.json"
    if not path.exists():
        return {}
    return {r["id"]: r for r in json.loads(path.read_text(encoding="utf-8"))["results"]}


def cell(result: dict | None) -> str:
    if not result:
        return "not run"
    if result.get("error"):
        return "error"
    tools = result["tools"]
    return "*(none)*" if not tools else ", ".join(f"`{t}`" for t in tools)


def main() -> int:
    fixtures = [
        json.loads(line) for line in FIXTURES.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    lg, crew = load("langgraph"), load("crewai")

    rows = []
    for fixture in fixtures:
        fid = fixture["id"]
        a, b = lg.get(fid), crew.get(fid)
        expected = ", ".join(f"`{t}`" for t in fixture["expect_tools"]) or "*(none)*"
        rows.append(
            f"| `{fid}` | {expected} | {cell(a)} | {cell(b)} "
            f"| {'yes' if a and a.get('gated') else 'no'} "
            f"| {'yes' if b and b.get('gated') else 'no'} |"
        )

    def score(results: dict) -> str:
        if not results:
            return "not run"
        ok = sum(1 for r in results.values() if r.get("correct_tools"))
        return f"{ok}/{len(results)}"

    def gated_writes(results: dict) -> str:
        if not results:
            return "not run"
        with_writes = [r for r in results.values() if r.get("writes")]
        gated = sum(1 for r in with_writes if r.get("gated"))
        return f"{gated}/{len(with_writes)}" if with_writes else "0/0"

    OUT.write_text(
        TEMPLATE.format(
            rows="\n".join(rows),
            lg_score=score(lg),
            crew_score=score(crew),
            lg_gated=gated_writes(lg),
            crew_gated=gated_writes(crew),
        ),
        encoding="utf-8",
    )
    print(f"wrote {OUT}")
    return 0


TEMPLATE = """# LangGraph vs CrewAI

Both stacks drive the **same MCP server** over stdio, with the same eight tools and the same ten
fixtures in `fixtures.jsonl`. Only the orchestration layer differs.

Scope is the plan-then-execute slice: turn a request into tool calls and run them. Retrieval, the
confidence gate and the streaming UI are not reimplemented in CrewAI — this is a framework
comparison, not a rewrite.

Regenerate:

```bash
cd backend  && ./.venv/Scripts/python.exe ../compare/run_langgraph.py
cd compare  && ./.venv/Scripts/python.exe run_crewai.py
cd compare  && ./.venv/Scripts/python.exe render_notes.py
```

## Per-fixture behaviour

| fixture | expected tools | LangGraph | CrewAI | LG gated | Crew gated |
|---|---|---|---|---|---|
{rows}

Correct tool set: **LangGraph {lg_score}**, **CrewAI {crew_score}**.
Writes stopped for human approval: **LangGraph {lg_gated}**, **CrewAI {crew_gated}**.

## Capability differences that mattered

| | LangGraph | CrewAI |
|---|---|---|
| Control flow | Explicit nodes and conditional edges; the path is a data structure you can print | Agent autonomy inside a task; the path is whatever the model decides |
| Durable state | `AsyncSqliteSaver`, resumable by `thread_id` | None built in |
| Human approval | `interrupt()` — the run stops, state persists, any process can resume it | `human_input=True` — blocks on stdin inside `kickoff()` |
| Approval after restart | Works. Verified by killing the backend mid-approval and completing it from a new PID | Not possible; the prompt lives in the running process |
| Streaming to a UI | Custom stream writer, one event per node | Callbacks, no per-node stream |
| Provider control | Groq SDK directly, so two API keys rotate on 429 | Reaches Groq through litellm; rotation is not exposed |
| Install footprint | 137 packages, 281 MB — including Qdrant, ONNX and FastAPI | 169 packages, 554 MB for the agent layer alone |

## Where each one is actually better

**CrewAI got the first working version faster.** One agent, one task, a tool list, and it ran. The
LangGraph version needed a state schema, six nodes, three conditional edge functions and a
checkpointer before it did anything at all. For a prototype that is a real advantage, and it is the
honest reason CrewAI is popular.

**LangGraph is the only one of the two that can do the thing this project exists to demonstrate.**
An approval gate that survives a process restart needs the run to be suspendable and its state to
be durable. `interrupt()` plus a checkpointer gives exactly that: the pause is a persisted state,
not a blocked thread. CrewAI's `human_input=True` is a console prompt inside `kickoff()` — fine for
a human at a terminal, unusable behind an HTTP API, and gone if the process dies.

That is the difference that decided the architecture. Everything else is preference.

## Friction found in CrewAI, with evidence

**Groq is unreachable without a workaround.** Groq is not one of CrewAI's native providers, so it
routes through litellm. CrewAI's agent executor marks messages with `cache_breakpoint: True` and
expects the provider adapter to translate or strip it — its own module docstring says adapters
"strip it for providers that cache implicitly ... or do not cache at all". The litellm path has no
such adapter, so the marker is sent as a message property and Groq rejects it:

```
GroqException - 'messages.0' : for 'role:system' the following must be satisfied
[('messages.0' : property 'cache_breakpoint' is unsupported)]
```

`compare/crew_impl.py` patches `litellm.completion` to strip the key. Without that, CrewAI plus
Groq does not run at all.

## Bugs this comparison found in the LangGraph implementation

Running the same fixtures through both stacks was worth more for what it exposed on my own side
than for the comparison itself.

1. **The corpus confidence gate was vetoing tool use.** `after_grade` refused any request whose
   retrieval score was low. But "who is on call right now" is correctly absent from every runbook,
   so it scored -7.5 and was refused — while the `find_oncall` tool answers it instantly. The gate
   measures whether the *corpus* can answer, not whether the *system* can. Action requests now
   reach the planner regardless of score, and refusal requires both a weak corpus and no tool
   results.
2. **The router's verb list missed "move" and "add".** `update-status` and `log-note` were
   classified as questions. Read-tool questions were missed entirely, so the router now also
   triggers on named entities — an email, a ticket, an asset tag, a rotation.
3. **The planner was told not to use tools for questions.** Its prompt said "if it only asks a
   question, call nothing", which suppressed every read tool. Questions about live state need a
   tool; questions about policy do not.
4. **Test isolation was leaking into the real database.** `PythonStdioTransport` does not pass the
   parent environment to the spawned server, so `ASOC_DB_PATH` was dropped and the first fixture
   run wrote its tickets into the seeded `asoc.db`. Both clients now pass `env` explicitly.
5. **Groq rejected a valid intent over a quoted integer.** For "Move ticket 1 to in-progress" the
   model emits `{{"ticket_id": "1"}}`, and Groq validates tool calls against the advertised schema
   and refuses. It reproduced across both API keys and at two temperatures, so it was systematic
   rather than a sampling fluke and retrying did not help. The schema sent to the model now accepts
   a string for integer parameters and the client coerces before dispatch, which keeps the MCP
   server's contract strict.

Only the first of those five was visible from the UI. The fixtures found the rest.

## Caveats on the numbers

Latency is not compared, because it would not be a like-for-like measurement: the LangGraph path
runs hybrid retrieval and cross-encoder reranking (about 1.1s on CPU) before planning, and the
CrewAI slice does no retrieval at all.

Package counts are per-venv and not strictly a framework comparison either — `backend` carries
Qdrant, ONNX runtime and FastAPI, while `compare` carries CrewAI, litellm and fastmcp. The point
worth keeping is the direction: CrewAI's agent layer alone is larger than the entire retrieval,
graph and API stack it is being compared against.
"""


if __name__ == "__main__":
    raise SystemExit(main())
