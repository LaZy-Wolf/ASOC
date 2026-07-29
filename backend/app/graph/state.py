"""Graph state.

Everything here is checkpointed, so everything must be JSON-serialisable — retrieval Hits become
plain dicts on the way in. That constraint is the whole reason a conversation can survive a
process restart mid-approval.
"""

from __future__ import annotations

from typing import TypedDict


class AgentState(TypedDict, total=False):
    # input
    query: str
    thread_id: str

    # router
    route: str  # lookup | multi_hop | action
    doc_type: str | None

    # retrieval
    hits: list[dict]
    top_score: float | None
    confident: bool
    injection_flags: list[str]

    # planning
    plan: list[dict]  # [{name, arguments}]
    blocked: list[dict]  # proposed calls not advertised by the MCP server

    # human-in-the-loop
    pending: list[dict]  # writes awaiting a decision
    decision: str | None  # approve | reject | auto

    # execution
    executed: list[dict]

    # output
    answer: str
    error: str | None
