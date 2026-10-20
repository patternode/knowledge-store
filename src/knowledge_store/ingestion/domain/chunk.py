"""Deterministic passage chunking.

A passage id is the document id plus the sha256 of its text, so re-refining an unchanged
document yields identical ids, and the same id names the passage in the graph and in the
portal's citations.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass

TARGET_CHARS = 1800
MAX_CHARS = 3000
CHUNKER_VERSION = "chunk@1"


@dataclass(frozen=True)
class Passage:
    passage_id: str
    doc_id: str
    seq: int
    char_start: int
    char_end: int
    content_hash: str
    text: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Passage":
        return cls(**{k: d[k] for k in cls.__dataclass_fields__})


def _hash(text: str) -> str:
    return hashlib.sha256(" ".join(text.split()).encode()).hexdigest()


def chunk_text(text: str, doc_id: str, target: int = TARGET_CHARS, max_chars: int = MAX_CHARS) -> list[Passage]:
    """Split on blank lines, pack paragraphs up to ~target chars, never splitting a line.
    Paragraphs longer than max_chars are split on line boundaries; a single line longer
    than max_chars is split on whitespace."""
    blocks: list[tuple[int, int]] = []
    pos = 0
    for para in text.split("\n\n"):
        start = text.find(para, pos)
        end = start + len(para)
        pos = end
        if not para.strip():
            continue
        if len(para) <= max_chars:
            blocks.append((start, end))
            continue
        line_start = start
        acc = start
        for line in para.split("\n"):
            ls = text.find(line, acc)
            le = ls + len(line)
            acc = le
            if le - line_start > max_chars and ls > line_start:
                blocks.append((line_start, ls - 1))
                line_start = ls
        blocks.append((line_start, end))

    split: list[tuple[int, int]] = []
    for s, e in blocks:
        while e - s > max_chars:
            cut = text.rfind(" ", s, s + max_chars)
            cut = cut if cut > s else s + max_chars
            split.append((s, cut))
            s = cut
        split.append((s, e))

    passages: list[Passage] = []
    cur_s: int | None = None
    cur_e = 0
    for s, e in split:
        if cur_s is None:
            cur_s, cur_e = s, e
        elif e - cur_s <= target:
            cur_e = e
        else:
            passages.append(_mk(text, cur_s, cur_e, doc_id, len(passages)))
            cur_s, cur_e = s, e
    if cur_s is not None:
        passages.append(_mk(text, cur_s, cur_e, doc_id, len(passages)))
    return [p for p in passages if p.text]


def _mk(text: str, s: int, e: int, doc_id: str, seq: int) -> Passage:
    body = text[s:e].strip()
    h = _hash(body)
    return Passage(passage_id=f"{doc_id[:16]}-p{seq:03d}-{h[:10]}", doc_id=doc_id, seq=seq,
                   char_start=s, char_end=e, content_hash=h, text=body)
