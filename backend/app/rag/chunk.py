"""Heading-aware markdown chunking.

The heading path ("Runbook: TLS Certificate Expiry > Renewal: automated certificates") is
*prepended to the chunk text*, not merely stored as metadata. Two reasons: retrieval matches
against it, and it gives the model the section's context when the chunk is quoted in isolation.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path

import yaml

MAX_CHARS = 1200
OVERLAP_CHARS = 150
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
NAMESPACE = uuid.UUID("6f9619ff-8b86-d011-b42d-00c04fc964ff")


@dataclass
class Chunk:
    id: str  # "doc-slug#3"
    text: str  # heading path + body
    doc_id: str
    heading_path: str
    meta: dict

    @property
    def point_id(self) -> str:
        """Deterministic Qdrant point id, so re-indexing updates rather than duplicates."""
        return str(uuid.uuid5(NAMESPACE, self.id))


def split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    return yaml.safe_load(parts[1]) or {}, parts[2].lstrip("\n")


def sections(body: str) -> list[tuple[str, str]]:
    """Split into (heading_path, text) pairs, one per heading block."""
    stack: list[tuple[int, str]] = []
    buf: list[str] = []
    out: list[tuple[str, str]] = []

    def flush() -> None:
        text = "\n".join(buf).strip()
        if text:
            out.append((" > ".join(title for _, title in stack), text))
        buf.clear()

    for line in body.splitlines():
        match = HEADING_RE.match(line)
        if not match:
            buf.append(line)
            continue
        flush()
        level = len(match.group(1))
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, match.group(2).strip()))

    flush()
    return out


def split_long(text: str) -> list[str]:
    """Pack paragraphs up to MAX_CHARS, carrying OVERLAP_CHARS across the seam.

    ponytail: a single paragraph longer than MAX_CHARS is emitted oversized rather than cut
    mid-sentence. Split it further only if the corpus starts carrying such paragraphs.
    """
    if len(text) <= MAX_CHARS:
        return [text]

    out: list[str] = []
    current = ""
    for para in re.split(r"\n\s*\n", text):
        if current and len(current) + len(para) + 2 > MAX_CHARS:
            out.append(current)
            current = current[-OVERLAP_CHARS:] + "\n\n" + para
        else:
            current = f"{current}\n\n{para}" if current else para
    if current:
        out.append(current)
    return out


def chunk_file(path: Path) -> list[Chunk]:
    meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
    doc_id = path.stem
    chunks: list[Chunk] = []

    for heading_path, text in sections(body):
        for part in split_long(text):
            chunks.append(
                Chunk(
                    id=f"{doc_id}#{len(chunks)}",
                    text=f"{heading_path}\n\n{part}" if heading_path else part,
                    doc_id=doc_id,
                    heading_path=heading_path,
                    meta={**meta, "source": path.name},
                )
            )
    return chunks


def chunk_corpus(corpus_dir: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(corpus_dir.glob("*.md")):
        chunks.extend(chunk_file(path))
    return chunks
