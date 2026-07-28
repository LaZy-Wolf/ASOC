from pathlib import Path

from app.rag.chunk import MAX_CHARS, Chunk, chunk_file, sections, split_frontmatter, split_long

# a packed chunk may exceed MAX_CHARS by the overlap it carries in
OVERLAP_SLACK = 200

DOC = """---
doc_type: runbook
department: platform
---

# Runbook: Thing

Intro text.

## Step One

Do the first thing.

### Detail

A nested detail.

## Step Two

Do the second thing.
"""


def test_frontmatter_parsed_and_stripped():
    meta, body = split_frontmatter(DOC)
    assert meta["doc_type"] == "runbook"
    assert body.startswith("# Runbook: Thing")


def test_no_frontmatter_passes_through():
    meta, body = split_frontmatter("# Just A Doc\n\nBody.")
    assert meta == {}
    assert body.startswith("# Just A Doc")


def test_heading_path_nests_and_pops():
    _, body = split_frontmatter(DOC)
    paths = [path for path, _ in sections(body)]
    assert "Runbook: Thing > Step One" in paths
    assert "Runbook: Thing > Step One > Detail" in paths
    # H2 after an H3 must pop back to depth 2, not stay nested under Detail
    assert "Runbook: Thing > Step Two" in paths


def test_heading_path_prepended_to_text(tmp_path: Path):
    path = tmp_path / "runbook-thing.md"
    path.write_text(DOC, encoding="utf-8")
    chunks = chunk_file(path)

    detail = next(c for c in chunks if c.heading_path.endswith("Detail"))
    assert detail.text.startswith("Runbook: Thing > Step One > Detail")
    assert "A nested detail." in detail.text
    assert detail.doc_id == "runbook-thing"
    assert detail.meta["doc_type"] == "runbook"


def test_long_section_splits_with_overlap():
    para = "x" * 400
    parts = split_long("\n\n".join([para] * 6))
    assert len(parts) > 1
    assert all(len(p) <= MAX_CHARS + OVERLAP_SLACK for p in parts)
    # the seam carries context forward
    assert parts[1].startswith("x")


def test_point_id_is_stable():
    chunk = Chunk(id="doc#0", text="t", doc_id="doc", heading_path="", meta={})
    same = Chunk(id="doc#0", text="different text", doc_id="doc", heading_path="", meta={})
    assert chunk.point_id == same.point_id
