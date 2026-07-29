"""Query routing and the confidence gate.

Routing is a keyword heuristic, not an LLM call. A classifier round trip would cost more latency
than the retrieval it is routing, and these three classes are separable by surface form.

The confidence threshold was calibrated, not guessed: over six answerable and six unanswerable
questions, top rerank scores were -1.9..+7.8 and -9.4..-11.3 respectively. -5.0 sits in the 7.5
point gap between the two clusters, with margin on each side. Recalibrate whenever the corpus or
the reranker changes — `eval/retrieval_eval.py` reports refusal precision so a bad threshold shows
up as a number rather than a surprise in production.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.rag.rerank import rerank
from app.rag.retrieve import Hit, hybrid_retrieve

Route = Literal["lookup", "multi_hop", "action"]

CONFIDENCE_THRESHOLD = -5.0
TOP_N = 5

ACTION_RE = re.compile(
    r"\b(open|create|file|raise|log|update|close|assign|schedule|book)\b[^.?!]{0,40}"
    r"\b(ticket|incident|window|meeting|request|access)\b",
    re.I,
)
MULTI_HOP_RE = re.compile(
    r"\b(difference between|compared? (?:to|with)|versus|vs\.?|both|as well as|and also)\b", re.I
)
# a doc-type word in the query is a usable metadata filter
DOC_TYPE_RE = re.compile(r"\b(runbook|policy|postmortem|guide)\b", re.I)


@dataclass
class SearchResult:
    route: Route
    hits: list[Hit]
    confident: bool
    top_score: float | None
    doc_type: str | None


def classify(query: str) -> Route:
    if ACTION_RE.search(query):
        return "action"
    if MULTI_HOP_RE.search(query):
        return "multi_hop"
    return "lookup"


def doc_type_filter(query: str) -> str | None:
    match = DOC_TYPE_RE.search(query)
    return match.group(1).lower() if match else None


def search(query: str, top_n: int = TOP_N) -> SearchResult:
    """Route, retrieve, rerank, and decide whether the result is good enough to answer from."""
    route = classify(query)
    doc_type = doc_type_filter(query)

    hits = rerank(query, hybrid_retrieve(query, doc_type=doc_type), top_n=top_n)

    # a doc_type filter that returns nothing is worse than no filter; retry unfiltered
    if not hits and doc_type:
        doc_type = None
        hits = rerank(query, hybrid_retrieve(query), top_n=top_n)

    top_score = hits[0].rerank_score if hits else None
    confident = top_score is not None and top_score >= CONFIDENCE_THRESHOLD

    return SearchResult(
        route=route, hits=hits, confident=confident, top_score=top_score, doc_type=doc_type
    )
