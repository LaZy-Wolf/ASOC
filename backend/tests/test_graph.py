"""Graph topology and routing.

These are the structural guarantees, tested without an LLM or a network call: an LLM in a test
would make the safety property probabilistic, and "no write reaches the database without a human"
is not a property that should hold only most of the time.
"""

import pytest

from app.graph.build import after_grade, after_plan, build
from app.mcp_client import WRITE_TOOLS, is_write

READ = {"name": "get_user", "arguments": {}}
WRITE = {"name": "create_ticket", "arguments": {}}


def test_graph_compiles_with_the_expected_topology():
    graph = build().compile().get_graph()
    assert {"router", "retrieve", "plan", "approve", "execute", "respond"} <= set(graph.nodes)


def test_low_corpus_confidence_does_not_veto_the_tool_path():
    """"Who is on call right now" scores badly against runbooks and is answered by a tool.

    Refusing it because the corpus was unconvincing was a real bug: the gate measures whether the
    *corpus* can answer, not whether the system can.
    """
    assert after_grade({"confident": False, "route": "action"}) == "plan"


def test_a_corpus_question_never_reaches_the_planner():
    assert after_grade({"confident": True, "route": "lookup"}) == "respond"
    assert after_grade({"confident": True, "route": "multi_hop"}) == "respond"


def test_an_unanswerable_non_action_question_is_refused():
    assert after_grade({"confident": False, "route": "lookup"}) == "respond"


def test_an_action_request_reaches_the_planner():
    assert after_grade({"confident": True, "route": "action"}) == "plan"


def test_reads_execute_without_approval():
    assert after_plan({"plan": [READ]}) == "execute"


def test_an_empty_plan_answers_rather_than_executing():
    assert after_plan({"plan": []}) == "respond"


@pytest.mark.parametrize("tool", sorted(WRITE_TOOLS))
def test_every_write_tool_routes_through_approval(tool):
    """The safety property, checked per tool so a new write tool cannot quietly bypass the gate."""
    assert after_plan({"plan": [{"name": tool, "arguments": {}}]}) == "approve"


def test_a_write_mixed_with_reads_still_requires_approval():
    assert after_plan({"plan": [READ, WRITE, READ]}) == "approve"


def test_write_classification_matches_the_server_tools():
    """Guards against a rename on the server silently turning a write into an ungated read."""
    assert is_write("create_ticket")
    assert not is_write("search_tickets")
    assert not is_write("find_oncall")
