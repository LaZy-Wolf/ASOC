"""Retrieval behaviour. Needs a running Qdrant with the corpus indexed.

Skipped rather than failed when Qdrant is unreachable, so `pytest` stays useful without Docker.
"""

from __future__ import annotations

import pytest

from app.rag.retrieve import COLLECTION, _client, dense_retrieve, hybrid_retrieve


def _index_ready() -> bool:
    try:
        return _client().collection_exists(COLLECTION) and _client().count(COLLECTION).count > 0
    except Exception:
        return False


needs_index = pytest.mark.skipif(not _index_ready(), reason="Qdrant not reachable or not indexed")


def rrf(ranks: list[int | None], k: int = 60) -> float:
    """Reference implementation of the fusion Qdrant applies server-side.

    A document scores sum(1 / (k + rank)) over the rankings it appears in, 1-indexed. k=60 is the
    value from the original paper and Qdrant's default. Its job is to flatten the difference
    between the very top ranks so that agreement across retrievers outweighs one retriever's
    enthusiasm.
    """
    return sum(1 / (k + rank) for rank in ranks if rank is not None)


def test_rrf_prefers_agreement_over_one_strong_opinion():
    """Ranked 3rd by both beats ranked 1st by one and 40th by the other."""
    agreed = rrf([3, 3])
    lopsided = rrf([1, 40])
    assert agreed > lopsided
    assert agreed == pytest.approx(2 / 63)
    assert lopsided == pytest.approx(1 / 61 + 1 / 100)


def test_rrf_k_controls_how_much_top_ranks_dominate():
    """With a small k the lopsided document wins; k=60 is what flips the comparison."""
    assert rrf([1, 40], k=1) > rrf([3, 3], k=1)
    assert rrf([1, 40], k=60) < rrf([3, 3], k=60)


def test_rrf_ignores_missing_ranks():
    assert rrf([5, None]) == pytest.approx(1 / 65)


@needs_index
def test_hybrid_finds_a_rare_exact_term_dense_ranks_poorly():
    """The case hybrid exists for: a literal identifier carries no semantic signal.

    "patronictl" appears only in the failover runbook. A dense model has no useful embedding for
    a command name it never saw; BM25 matches it exactly.
    """
    query = "patronictl"
    hybrid_docs = [h.doc_id for h in hybrid_retrieve(query, top_k=3)]
    assert "runbook-database-failover" in hybrid_docs


@needs_index
def test_metadata_filter_restricts_to_one_doc_type():
    hits = hybrid_retrieve("what went wrong", top_k=5, doc_type="postmortem")
    assert hits, "filter should not empty the result for a term present in postmortems"
    assert {h.doc_type for h in hits} == {"postmortem"}


@needs_index
def test_dense_baseline_still_returns_requested_count():
    """The baseline stays wired up — the eval table depends on it."""
    assert len(dense_retrieve("how long is an on-call shift", top_k=5)) == 5
