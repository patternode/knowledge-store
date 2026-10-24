"""Sections of conformed text, cut before passages are packed.

A section is a heading and the body it introduces, a fenced block, or the prose
between them. Plain text has no headings: the caller packs it as paragraphs.
Markdown and HTML do, and HTML headings are written as the same `#` lines.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_ATX = re.compile(r"#{1,6}[ \t]+\S")
_SETEXT = re.compile(r"(?:=|-){3,}")
_FENCE = "```"


@dataclass(frozen=True)
class Section:
    kind: str  # prose or fence
    start: int
    end: int


def sections(text: str, *, headings: bool) -> list[Section]:
    """Spans that cover the text. Headings are boundaries only when asked."""
    if not text:
        return []
    lines = _lines(text)
    if not headings:
        return [Section("prose", 0, len(text))]
    fenced = _fenced(lines)
    heads = _heads(lines, fenced) if headings else set()
    cuts = _cuts(lines, fenced, heads)
    spans: list[Section] = []
    for index, (start, kind) in enumerate(cuts):
        end = cuts[index + 1][0] if index + 1 < len(cuts) else len(text)
        if end > start:
            spans.append(Section(kind, start, end))
    return spans or [Section("prose", 0, len(text))]


def _lines(text: str) -> list[tuple[int, int, str]]:
    rows = []
    pos = 0
    for line in text.split("\n"):
        rows.append((pos, pos + len(line), line))
        pos += len(line) + 1
    return rows


def _fenced(lines: list[tuple[int, int, str]]) -> set[int]:
    inside: set[int] = set()
    open_ = False
    for index, (_, _, content) in enumerate(lines):
        if content.lstrip().startswith(_FENCE):
            inside.add(index)
            open_ = not open_
            continue
        if open_:
            inside.add(index)
    return inside


def _heads(lines: list[tuple[int, int, str]], fenced: set[int]) -> set[int]:
    heads: set[int] = set()
    index = 0
    while index < len(lines):
        if index in fenced:
            index += 1
            continue
        content = lines[index][2]
        if _ATX.match(content):
            heads.add(index)
            index += 1
            continue
        nxt = index + 1
        if (nxt < len(lines) and nxt not in fenced and content.strip()
                and _SETEXT.fullmatch(lines[nxt][2].strip()) and not content.lstrip().startswith("#")):
            heads.add(index)
            index += 2
            continue
        index += 1
    return heads


def _cuts(lines: list[tuple[int, int, str]], fenced: set[int],
          heads: set[int]) -> list[tuple[int, str]]:
    cuts: list[tuple[int, str]] = [(0, "prose")]
    index = 0
    while index < len(lines):
        if index in fenced:
            start = lines[index][0]
            while index < len(lines) and index in fenced:
                index += 1
            _add(cuts, start, "fence")
            if index < len(lines):
                _add(cuts, lines[index][0], "prose")
            continue
        if index in heads:
            _add(cuts, lines[index][0], "prose")
        index += 1
    return cuts


def _add(cuts: list[tuple[int, str]], start: int, kind: str) -> None:
    if cuts and cuts[-1][0] == start:
        cuts[-1] = (start, kind)
        return
    if start > 0 or not cuts:
        cuts.append((start, kind))
