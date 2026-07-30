"""Routing decisions.

Every case here came from a fixture in compare/fixtures.jsonl that the router originally got
wrong: it answered "who is on call" from the runbooks instead of asking the on-call tool, and it
missed "move ticket 1" because its verb list had no "move".
"""

import pytest

from app.rag.route import classify, doc_type_filter, needs_tools

NEEDS_TOOLS = [
    "Open a P3 hardware ticket for mira.kovac@example.com — her laptop will not power on.",
    "Move ticket 1 to in-progress.",
    "Add a note to ticket 1 saying the profile was re-added.",
    "Who is on call for the platform team right now?",
    "What is the warranty status of asset LT-4388?",
    "Are there any open tickets already mentioning VPN?",
    "Book a maintenance window for identity under change CHG-2001.",
    "Look up dev.mehta@example.com and open a P4 access request for him.",
    "Mark the priority on ticket 3 as P2.",
]

CORPUS_ONLY = [
    "What is our escalation policy for a P1 outage?",
    "My VPN connects then drops after a minute. What now?",
    "What severity is a database host at 96 percent disk?",
    "How long is an on-call shift?",  # names the rotation, but see below
    "Why did the rollback not fix the login failures in May?",
    "How much memory does a new engineering laptop come with?",
]


@pytest.mark.parametrize("query", NEEDS_TOOLS)
def test_tool_bearing_requests_reach_the_planner(query):
    assert needs_tools(query)
    assert classify(query) == "action"


@pytest.mark.parametrize("query", [q for q in CORPUS_ONLY if "on-call shift" not in q])
def test_policy_questions_do_not_reach_the_planner(query):
    assert not needs_tools(query)
    assert classify(query) != "action"


def test_on_call_phrasing_is_deliberately_over_inclusive():
    """"How long is an on-call shift" is a policy question, but it names the rotation.

    It routes to the planner, which sees the tool schemas, calls nothing, and the answer still
    comes from the corpus. The cost is one wasted planning call; the alternative — a false
    negative on "who is on call right now" — answers from a policy document instead of live data.
    """
    assert needs_tools("How long is an on-call shift?")


def test_multi_hop_is_detected_when_no_tools_are_implied():
    assert classify("What is the difference between severity and escalation?") == "multi_hop"


def test_doc_type_filter_picks_up_an_explicit_type():
    assert doc_type_filter("what does the postmortem say about the outage") == "postmortem"
    assert doc_type_filter("how do I reset my password") is None
