"""Graph wiring and the checkpointer.

    router -> retrieve -> grade -+- not confident ------------------> respond
                                 +- confident, not an action ------> respond
                                 +- confident action -> plan -+- writes -> approve -+-> execute
                                                              +- reads only ------->|
                                                                                    v
                                                                                 respond

`approve` is where interrupt() fires. State lives in SQLite, so a conversation paused for
approval survives the process that started it.
"""

from __future__ import annotations

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph

from app.config import ROOT
from app.graph import nodes
from app.graph.state import AgentState
from app.mcp_client import is_write

CHECKPOINT_DB = ROOT / "backend" / "checkpoints.db"


def after_grade(state: AgentState) -> str:
    """Low corpus confidence must not veto the tool path.

    The confidence score says whether the *corpus* can answer, and "who is on call right now" is
    correctly absent from every runbook. Treating that as "we cannot answer" refused questions the
    MCP tools answer trivially. So an action request reaches the planner regardless of score, and
    only a non-action request with no corpus support is refused.
    """
    if state.get("route") == "action":
        return "plan"
    return "respond"


def after_plan(state: AgentState) -> str:
    if not state.get("plan"):
        return "respond"
    return "approve" if any(is_write(c["name"]) for c in state["plan"]) else "execute"


def after_approve(state: AgentState) -> str:
    """A rejection still runs execute, which drops the writes and keeps any reads."""
    return "execute"


def build() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("router", nodes.router)
    graph.add_node("retrieve", nodes.retrieve)
    graph.add_node("plan", nodes.plan)
    graph.add_node("approve", nodes.approve)
    graph.add_node("execute", nodes.execute)
    graph.add_node("respond", nodes.respond)

    graph.add_edge(START, "router")
    graph.add_edge("router", "retrieve")
    graph.add_conditional_edges("retrieve", after_grade, ["plan", "respond"])
    graph.add_conditional_edges("plan", after_plan, ["approve", "execute", "respond"])
    graph.add_conditional_edges("approve", after_approve, ["execute"])
    graph.add_edge("execute", "respond")
    graph.add_edge("respond", END)

    return graph


def checkpointer() -> AsyncSqliteSaver:
    """Durable state. from_conn_string is an async context manager, so callers hold it open for
    the lifetime of the app rather than per request — a per-request connection would drop the
    interrupt state between the pause and the approval."""
    return AsyncSqliteSaver.from_conn_string(str(CHECKPOINT_DB))
