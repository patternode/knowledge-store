"""Deterministic passage chunking.

A passage id is the document id plus the sha256 of its text, so re-refining an unchanged
document yields identical ids, and the same id names the passage in the graph and in the
portal's citations.

chunk@1 packs paragraphs and may cross a heading. chunk@2, which refine uses, asks the
sections module for boundaries first. A parser without headings still packs as chunk@1,
so a plain-text document keeps the same passages.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass

from knowledge_store.ingestion.domain.sections import sections

TARGET_CHARS = 1800
MAX_CHARS = 3000
CHUNKER_VERSION = "chunk@1"
SECTION_CHUNKER = "chunk@2"
_HEADED_PARSERS = {"markdown@1", "html@1"}
_ATX = re.compile(r"#{1,6}[ \t]+\S")
_SENTENCE = re.compile(r"(?<=[.!?])\s+")


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


def chunk_document(text: str, doc_id: str, *, parser: str,
                   target: int = TARGET_CHARS, max_chars: int = MAX_CHARS) -> list[Passage]:
    """Pack passages for one parsed document.

    Markdown and HTML cut on headings and fences. A table packs one row at a time.
    Every other parser packs paragraphs, which is chunk@1. The silver document records
    SECTION_CHUNKER either way, because this is the step refine runs.
    """
    if parser == "table@1":
        return _chunk_rows(text, doc_id, target, max_chars)
    if parser not in _HEADED_PARSERS:
        return chunk_text(text, doc_id, target=target, max_chars=max_chars)
    passages: list[Passage] = []
    for section in sections(text, headings=True):
        if section.kind == "fence":
            blocks = _hard_blocks(text, section.start, section.end, max_chars)
        else:
            blocks = _region_blocks(text, section.start, section.end, max_chars)
            blocks = _keep_heading(text, blocks, max_chars)
        passages.extend(_pack(text, blocks, doc_id, target, len(passages)))
    return [p for p in passages if p.text]


def chunk_regions(text: str, regions: list[tuple[int, int]], doc_id: str, *,
                  parser: str, target: int = TARGET_CHARS,
                  max_chars: int = MAX_CHARS) -> list[Passage]:
    """Pack each region on its own, so a page or a part never joins the next one."""
    passages: list[Passage] = []
    for start, end in regions:
        local = chunk_document(text[start:end], doc_id, parser=parser, target=target, max_chars=max_chars)
        for passage in local:
            passages.append(_shift(passage, start, len(passages)))
    return [p for p in passages if p.text]


def _shift(passage: Passage, start: int, seq: int) -> Passage:
    moved = Passage(
        passage_id="", doc_id=passage.doc_id, seq=seq,
        char_start=passage.char_start + start, char_end=passage.char_end + start,
        content_hash=passage.content_hash, text=passage.text,
    )
    return _mk_from(moved)


def _mk_from(passage: Passage) -> Passage:
    """Rebuild the id from the sequence. The content hash stays."""
    return Passage(
        passage_id=f"{passage.doc_id[:16]}-p{passage.seq:03d}-{passage.content_hash[:10]}",
        doc_id=passage.doc_id, seq=passage.seq, char_start=passage.char_start,
        char_end=passage.char_end, content_hash=passage.content_hash, text=passage.text,
    )


def _chunk_rows(text: str, doc_id: str, target: int, max_chars: int) -> list[Passage]:
    """One block per row. A row longer than the cap breaks between cells, never through one."""
    blocks: list[tuple[int, int]] = []
    pos = 0
    for line in text.split("\n"):
        start, end = pos, pos + len(line)
        pos = end + 1
        if not line.strip():
            continue
        if end - start <= max_chars:
            blocks.append((start, end))
        else:
            blocks.extend(_split_row(text, start, end, max_chars))
    return _pack(text, blocks, doc_id, target, 0)


def _cells(text: str, start: int, end: int) -> list[tuple[int, int]]:
    cells: list[tuple[int, int]] = []
    cursor = start
    while cursor < end:
        found = text.find(" | ", cursor, end)
        if found < 0:
            cells.append((cursor, end))
            break
        cells.append((cursor, found))
        cursor = found + 3
    return cells


def _split_row(text: str, start: int, end: int, max_chars: int) -> list[tuple[int, int]]:
    """Pack whole cells up to the cap. A cell longer than the cap is split on its own."""
    blocks: list[tuple[int, int]] = []
    buf_s: int | None = None
    buf_e = start
    for cell_s, cell_e in _cells(text, start, end):
        if cell_e - cell_s > max_chars:
            if buf_s is not None:
                blocks.append((buf_s, buf_e))
                buf_s = None
            blocks.extend(_hard_blocks(text, cell_s, cell_e, max_chars))
            continue
        if buf_s is None:
            buf_s, buf_e = cell_s, cell_e
        elif cell_e - buf_s <= max_chars:
            buf_e = cell_e
        else:
            blocks.append((buf_s, buf_e))
            buf_s, buf_e = cell_s, cell_e
    if buf_s is not None:
        blocks.append((buf_s, buf_e))
    return blocks


def _region_blocks(text: str, start: int, end: int, max_chars: int) -> list[tuple[int, int]]:
    region = text[start:end]
    blocks: list[tuple[int, int]] = []
    pos = 0
    for para in region.split("\n\n"):
        rel = region.find(para, pos)
        if rel < 0:
            continue
        abs_s = start + rel
        abs_e = abs_s + len(para)
        pos = rel + len(para)
        if not para.strip():
            continue
        if abs_e - abs_s <= max_chars:
            blocks.append((abs_s, abs_e))
        else:
            blocks.extend(_hard_blocks(text, abs_s, abs_e, max_chars))
    return blocks


def _hard_blocks(text: str, start: int, end: int, max_chars: int) -> list[tuple[int, int]]:
    """Pieces of at most max_chars. A sentence end wins, then a space, then the limit."""
    blocks: list[tuple[int, int]] = []
    cursor = start
    while end - cursor > max_chars:
        window = text[cursor:cursor + max_chars]
        sentence = 0
        for matched in _SENTENCE.finditer(window):
            sentence = matched.end()
        if sentence > 0:
            cut = cursor + sentence
        else:
            space = window.rfind(" ")
            line = window.rfind("\n")
            gap = max(space, line)
            cut = cursor + gap if gap > 0 else cursor + max_chars
        blocks.append((cursor, cut))
        cursor = cut
    if cursor < end:
        blocks.append((cursor, end))
    return blocks


def _keep_heading(text: str, blocks: list[tuple[int, int]], max_chars: int) -> list[tuple[int, int]]:
    """The heading stays on the first passage of its section."""
    if len(blocks) < 2:
        return blocks
    h0, h1 = blocks[0]
    first = text[h0:h1].strip()
    if not _heading_block(first):
        return blocks
    b0, b1 = blocks[1]
    if b1 - h0 <= max_chars:
        return [(h0, b1), *blocks[2:]]
    room = max_chars - (b0 - h0)
    if room <= 1:
        return blocks
    fitted = _hard_blocks(text, b0, b1, room)
    if not fitted:
        return blocks
    head_end = fitted[0][1]
    return [(h0, head_end), *fitted[1:], *blocks[2:]]


def _heading_block(block: str) -> bool:
    lines = [line.strip() for line in block.split("\n") if line.strip()]
    if not lines:
        return False
    if _ATX.match(lines[0]):
        return True
    return len(lines) >= 2 and bool(re.fullmatch(r"(?:=|-){3,}", lines[-1]))


def _pack(text: str, blocks: list[tuple[int, int]], doc_id: str, target: int,
          seq: int) -> list[Passage]:
    passages: list[Passage] = []
    cur_s: int | None = None
    cur_e = 0
    for s, e in blocks:
        if cur_s is None:
            cur_s, cur_e = s, e
        elif e - cur_s <= target:
            cur_e = e
        else:
            passages.append(_mk(text, cur_s, cur_e, doc_id, seq + len(passages)))
            cur_s, cur_e = s, e
    if cur_s is not None:
        passages.append(_mk(text, cur_s, cur_e, doc_id, seq + len(passages)))
    return passages


def _mk(text: str, s: int, e: int, doc_id: str, seq: int) -> Passage:
    body = text[s:e].strip()
    h = _hash(body)
    return Passage(passage_id=f"{doc_id[:16]}-p{seq:03d}-{h[:10]}", doc_id=doc_id, seq=seq,
                   char_start=s, char_end=e, content_hash=h, text=body)
