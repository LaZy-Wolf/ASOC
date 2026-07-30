# LangGraph vs CrewAI

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

## Last observed LangGraph run

Recorded by hand from the run of 2026-07-30, after the router and planner fixes and before the
argument-coercion fix. This is transcribed rather than generated because the free-tier daily cap was
reached before the suite could be rerun; `results_langgraph.json` is deliberately absent rather than
holding a stale run.

| fixture | tools called | gated | correct |
|---|---|---|---|
| `create-hardware` | `get_user`, `create_ticket` | yes | yes |
| `create-network-p2` | `get_user`, `create_ticket` | yes | yes |
| `lookup-only-oncall` | `find_oncall` | no | yes |
| `lookup-only-asset` | `get_asset` | no | yes |
| `search-duplicates` | `search_tickets` | no | yes |
| `update-status` | *(none)* — Groq rejected `{"ticket_id": "1"}` | no | no |
| `log-note` | `log_interaction` | yes | yes |
| `schedule-window` | `schedule_maintenance_window` | yes | yes |
| `lookup-then-create` | `get_user`, `create_ticket` | yes | yes |
| `no-action-question` | *(none)* | no | yes |

**9/10 correct. Every write gated: 5/5.** The one failure is bug 5 below, since fixed and verified
directly, though not yet reconfirmed across the whole suite.

## Per-fixture behaviour (generated)

| fixture | expected tools | LangGraph | CrewAI | LG gated | Crew gated |
|---|---|---|---|---|---|
| `create-hardware` | `create_ticket` | not run | not run | no | no |
| `create-network-p2` | `create_ticket` | not run | not run | no | no |
| `lookup-only-oncall` | `find_oncall` | not run | not run | no | no |
| `lookup-only-asset` | `get_asset` | not run | not run | no | no |
| `search-duplicates` | `search_tickets` | not run | not run | no | no |
| `update-status` | `update_ticket` | not run | not run | no | no |
| `log-note` | `log_interaction` | not run | not run | no | no |
| `schedule-window` | `schedule_maintenance_window` | not run | not run | no | no |
| `lookup-then-create` | `get_user`, `create_ticket` | not run | not run | no | no |
| `no-action-question` | *(none)* | not run | not run | no | no |

Correct tool set: **LangGraph not run**, **CrewAI not run**.
Writes stopped for human approval: **LangGraph not run**, **CrewAI not run**.

> **Status of this table.** The CrewAI column is incomplete: Groq's free tier enforces 100,000
> tokens per day per *organisation*, and the CrewAI run exhausted it. CrewAI's ReAct loop issues
> several model calls per task where the LangGraph path issues two, so it burns the budget
> considerably faster — which is itself a difference worth knowing, though the numbers here are too
> coarse to quantify it.
>
> Switching CrewAI to Gemini (`ASOC_CREW_MODEL=gemini`, a CrewAI *native* provider that needs no
> litellm workaround) did not help: the Gemini key on this machine reports
> `generate_content_free_tier_requests, limit: 0` — no free-tier quota provisioned at all.
>
> The single-request path was verified working end to end on Groq before the cap was reached:
> `find_oncall` returned the correct primary and secondary through CrewAI's tool wrapper. Rerun the
> two commands above once quota resets to complete the column.
>
> The `update-status` row for LangGraph also predates the argument-coercion fix in
> `backend/app/mcp_client.py`. That fix is verified directly — `{"ticket_id": "1"}` is coerced to
> `1` and the call succeeds — but the suite has not been rerun since.

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
   model emits `{"ticket_id": "1"}`, and Groq validates tool calls against the advertised schema
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
