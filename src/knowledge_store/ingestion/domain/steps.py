"""The pure refine steps, in order.

Parsing lives in parsing.py. Conformance lives in the conform package, one module
per literal family. Sections live in sections.py. Passages are packed in chunk.py.
This module runs conform, then section and chunk. The slice only reads and writes
the lake.
"""

from __future__ import annotations

from dataclasses import dataclass

from knowledge_store.ingestion.domain.chunk import SECTION_CHUNKER, Passage, chunk_document
from knowledge_store.ingestion.domain.conform import CONFORMER_VERSION, conform
from knowledge_store.ingestion.domain.parsing import ParseResult


@dataclass(frozen=True)
class SilverBody:
    text: str
    title: str | None
    rules: tuple[dict, ...]
    passages: list[Passage]
    conformer: str
    chunker: str


def silver_body(parsed: ParseResult, doc_id: str) -> SilverBody:
    """Conformed text and the passages cut from it. The title is conformed on its own."""
    conformed = conform(parsed.text)
    title = conform(parsed.title).text if parsed.title else None
    passages = chunk_document(conformed.text, doc_id, parser=parsed.parser)
    return SilverBody(conformed.text, title, conformed.rules, passages,
                      CONFORMER_VERSION, SECTION_CHUNKER)
