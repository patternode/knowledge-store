"""The pure refine steps, in order.

Parsing lives in parsing.py. Conformance lives in the conform package, one module
per literal family. Sections live in sections.py. Passages are packed in chunk.py.
This module runs conform, then section and chunk. The slice only reads and writes
the lake.
"""

from __future__ import annotations

from dataclasses import dataclass

from knowledge_store.ingestion.domain.chunk import (
    SECTION_CHUNKER, Passage, chunk_document, chunk_regions,
)
from knowledge_store.ingestion.domain.conform import CONFORMER_VERSION, conform
from knowledge_store.ingestion.domain.conform.log import _EXAMPLES
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
    """Conformed text and the passages cut from it. The title is conformed on its own.

    A document with parts, such as a PDF page, is conformed and packed per part.
    """
    title = conform(parsed.title).text if parsed.title else None
    if parsed.parts:
        done = [conform(part) for part in parsed.parts]
        text, regions = _join([item.text for item in done])
        passages = chunk_regions(text, regions, doc_id, parser=parsed.parser)
        rules = _merge(item.rules for item in done)
        return SilverBody(text, title, rules, passages, CONFORMER_VERSION, SECTION_CHUNKER)
    conformed = conform(parsed.text)
    passages = chunk_document(conformed.text, doc_id, parser=parsed.parser)
    return SilverBody(conformed.text, title, conformed.rules, passages,
                      CONFORMER_VERSION, SECTION_CHUNKER)


def _join(parts: list[str]) -> tuple[str, list[tuple[int, int]]]:
    chunks: list[str] = []
    regions: list[tuple[int, int]] = []
    at = 0
    for text in parts:
        if not text:
            continue
        if chunks:
            chunks.append("\n\n")
            at += 2
        regions.append((at, at + len(text)))
        chunks.append(text)
        at += len(text)
    return "".join(chunks), regions


def _merge(groups) -> tuple[dict, ...]:
    counts: dict[str, int] = {}
    examples: dict[str, list[str]] = {}
    for rules in groups:
        for row in rules:
            name = row["rule"]
            counts[name] = counts.get(name, 0) + row["applied"]
            held = examples.setdefault(name, [])
            for example in row["examples"]:
                if example not in held and len(held) < _EXAMPLES:
                    held.append(example)
    return tuple({"rule": name, "applied": counts[name], "examples": examples[name]}
                 for name in sorted(counts) if counts[name])
