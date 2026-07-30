# ASOC — Agentic Support & Operations Copilot

An internal IT helpdesk copilot that both **knows** things and **does** things. It answers from a
corpus of runbooks and policies with citations, and it acts through tools on a real store — but
every write stops and waits for a human, and that pause survives a process restart.

Runs entirely locally on free tiers. No paid API required.

```
                        +---------------------------+
                        |  Next.js chat + approval  |
                        |  + live graph trace strip |
                        +-------------+-------------+
                                      |  SSE, one event per node
                                      v
                        +---------------------------+
                        |  LangGraph orchestrator   |  checkpointed, resumable
                        |  router -> retrieve ->    |
                        |  grade -> plan -> approve |
                        |  -> execute -> respond    |
                        +----+-----------------+----+
                             |                 |
              (retrieve)     v                 v    (act)
        +--------------------+---+     +-------+--------------------+
        |  Production RAG        |     |  Your MCP server          |
        |  dense + BM25 -> RRF   |     |  8 tools over SQLite,     |
        |  -> cross-encoder      |     |  4 read / 4 write         |
        |  -> confidence gate    |     |  spoken over stdio        |
        +------------------------+     +----------------------------+
                                               ^
                             +-----------------+
                             |  interrupt() before every write
                    +------------------------+
                    |  Human approval gate   |
                    +------------------------+
```

## What is actually interesting here

**Retrieval is measured, not asserted.** [`backend/eval/RESULTS.md`](backend/eval/RESULTS.md) is
generated from 91 questions — 81 answerable, 10 deliberately unanswerable:

| config | recall@5 | MRR | nDCG@5 | refusal recall | false refusal | p50 |
|---|---|---|---|---|---|---|
| dense top-k (baseline) | 0.864 | 0.735 | 0.761 | n/a | n/a | 15ms |
| hybrid RRF | 0.907 | 0.771 | 0.798 | n/a | n/a | 17ms |
| hybrid + rerank | 0.932 | 0.796 | 0.826 | 0.900 | 0.062 | 1143ms |

**Reranking is not there for the ranking.** It buys 36% of the recall gain for 77x the baseline
latency, which alone would be a poor trade. Its real job is producing an *absolute* relevance
score. RRF is rank-derived, so an unanswerable question can score the maximum — measured, the
answerable and unanswerable RRF ranges overlap completely. Without a cross-encoder there is
nothing to threshold, and the refusal gate cannot exist.

**The refusal threshold is an operating point, not a separation.** The two score distributions
overlap, so `RESULTS.md` publishes the whole curve and states the chosen point and why it leans
toward refusing: inventing an access policy is worse than an unnecessary "I don't know".

**The approval gate is durable.** A write pauses the graph, and the pause is persisted state rather
than a blocked thread — so a *different process* can approve it. That is the property CrewAI cannot
match, and the reason the architecture is a state machine; see
[`compare/NOTES.md`](compare/NOTES.md).

## Stack

| Layer | Choice |
|---|---|
| Orchestration | LangGraph state machine + `AsyncSqliteSaver` checkpointer |
| Retrieval | Qdrant, dense `bge-small-en-v1.5` + BM25 sparse, server-side RRF fusion |
| Reranking | `bge-reranker-base` cross-encoder via fastembed (ONNX, CPU) |
| Tools | Your own MCP server (FastMCP) over stdio, SQLite-backed |
| Generation | Groq `llama-3.3-70b-versatile`, two keys rotated, Gemini fallback |
| Backend | FastAPI, SSE streaming |
| Frontend | Next.js 15, Tailwind v4 |
| Tracing | Langfuse, self-hosted, optional at runtime |
| Eval | Deterministic recall/MRR/nDCG — no LLM judge in the loop |

## Run it

Needs Docker, Node 20+, and Python 3.12. Paste your keys into `.env` first — see
[`.env.example`](.env.example).

```bash
docker compose up -d
```

```bash
cd backend && uv venv --python 3.12 && uv pip install -r pyproject.toml pytest
```

```bash
cd mcp-server && uv venv --python 3.12 && uv pip install -r pyproject.toml pytest
```

Index the corpus once — this is the only place embeddings are computed, and the first run downloads
the models:

```bash
cd backend && ./.venv/Scripts/python.exe -m app.rag.index
```

Then the two services:

```bash
cd backend && ./.venv/Scripts/python.exe -m uvicorn app.main:app --port 8001
```

```bash
cd frontend && npm install && npm run dev
```

| Service | URL |
|---|---|
| App | http://localhost:3002 |
| API | http://localhost:8001 |
| Langfuse | http://localhost:3001 |
| Qdrant | http://localhost:6333/dashboard |

Ports are 8001/3002 rather than 8000/3000 because the machine this was built on runs another
project there. CORS accepts any localhost port, so moving them costs nothing.

## Try these

| Ask | What it exercises |
|---|---|
| *My VPN connects then drops after a minute* | The confusable-pair trap: the *setup* guide also contains "VPN used to work and has stopped". Dense-only ranked the wrong document first; hybrid + rerank puts the right chunk at rank 1. |
| *What severity is a database host at 96% disk?* | Multi-hop — reconciles the disk runbook with a corrected threshold from a postmortem's action items. |
| *What is our parental leave policy?* | Refusal. Scores below threshold, cites nothing, calls no LLM. |
| *Who is on call for platform right now?* | A question the corpus cannot answer and a tool can. |
| *Open a P3 hardware ticket for mira.kovac@example.com* | The approval gate. Nothing is written until you click. |

## Verify the interesting claims yourself

Regenerate the eval table:

```bash
cd backend && ./.venv/Scripts/python.exe -m eval.retrieval_eval
```

Prove the approval gate is durable — ask for a ticket, kill the backend, restart it, then approve:

```bash
curl -s -X POST http://localhost:8001/chat -H "Content-Type: application/json" -d "{\"message\":\"Open a P2 network ticket for owen.brooks@example.com, wifi is down\"}"
```

```bash
curl -s http://localhost:8001/thread/PASTE_THREAD_ID
```

```bash
curl -s -X POST http://localhost:8001/approve -H "Content-Type: application/json" -d "{\"thread_id\":\"PASTE_THREAD_ID\",\"decision\":\"approve\"}"
```

Run the tests:

```bash
cd backend && ./.venv/Scripts/python.exe -m pytest -q
```

```bash
cd mcp-server && ./.venv/Scripts/python.exe -m pytest -q
```

## Use the MCP server from Claude Desktop

The tools are a plain MCP server, so any MCP client can drive them. Setup and the config snippet
are in [`mcp-server/README.md`](mcp-server/README.md).

## Layout

```
backend/app/rag/     chunk, index, retrieve, rerank, route — the retrieval pipeline
backend/app/graph/   state, nodes, build — the LangGraph state machine
backend/app/         mcp_client, guard, llm, tracing
backend/eval/        golden_set.jsonl, retrieval_eval.py, RESULTS.md
mcp-server/          server.py (8 tools), db.py (SQLite)
frontend/            Next.js console: log, evidence rail, approval card, trace strip
data/corpus/         20 IT operations documents
compare/             CrewAI reimplementation of the plan-execute slice + NOTES.md
plan.md              build plan, phase status, and every decision that changed on measurement
```

## Notes and limits

- **Local only.** No deploy target. Qdrant plus the ONNX models do not fit a 512MB free instance,
  and the point of the project is the pipeline, not the hosting.
- **Groq's daily token limit is per organisation, not per key.** Two keys from one org share one
  budget, so rotation helps the per-minute limit and not the daily one — a real limitation of the
  rotation design, found by exhausting it.
- **The Gemini fallback needs a key with quota.** The key used during development reports
  `generate_content_free_tier_requests, limit: 0` — no free-tier allowance provisioned — so the
  fallback path has never actually served a request. It is wired and logged but unproven; check
  your key at https://ai.dev/rate-limit before relying on it.
- **Reranking is ~1.1s on CPU.** That is the honest cost of a 278M cross-encoder without a GPU.
  `RERANK_CANDIDATES` in `retrieve.py` is the latency dial, and the sweep behind the chosen value
  of 8 is in the comments there.
- **Tracing is optional.** Missing or wrong Langfuse keys log a warning and the graph runs
  untraced. Create a project in the Langfuse UI and paste its generated keys into `.env` to enable
  it.
- **A demo recording is not included yet.** Record the approval flow at http://localhost:3002 and
  drop it in as `docs/demo.gif`.
