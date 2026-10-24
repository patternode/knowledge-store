"""Convert HTML documents into plain text that keeps table rows on one line.

Reports often carry most of their numbers in tables, so each <tr> becomes
one line with cells separated by " | ". Standard library only, so the Lambda
and Fargate images stay small.
"""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser

_BLOCK = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "table", "section"}
_HEADING = {"h1": "#", "h2": "##", "h3": "###", "h4": "####", "h5": "#####", "h6": "######"}
_SKIP = {"script", "style", "head", "title"}


class _Extractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0
        self.in_cell = False
        self.row: list[str] = []
        self.cell: list[str] = []
        self.title: list[str] | None = None  # the first <title>'s text, collected while inside it
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        if tag == "title" and self.title is None:
            self.title, self.in_title = [], True
        if tag in _SKIP:
            self.skip += 1
        elif tag in ("td", "th"):
            self.in_cell = True
            self.cell = []
        elif tag == "tr":
            self.row = []
        elif tag in _HEADING:
            self.parts.append("\n" + _HEADING[tag] + " ")
        elif tag in _BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag in _SKIP:
            self.skip = max(0, self.skip - 1)
        elif tag in ("td", "th"):
            text = " ".join("".join(self.cell).split())
            if text:
                self.row.append(text)
            self.in_cell = False
        elif tag == "tr":
            if self.row:
                self.parts.append("\n" + _join_row(self.row) + "\n")
            self.row = []
        elif tag in _HEADING:
            self.parts.append("\n")
        elif tag in _BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.in_title:
            self.title.append(data)
        if self.skip:
            return
        if self.in_cell:
            self.cell.append(data)
        else:
            self.parts.append(data)


def _join_row(cells: list[str]) -> str:
    # Glue "$" and "%" cells and parenthesised negatives to their numbers.
    merged: list[str] = []
    for c in cells:
        if merged and (c in ("%", ")", "%)") or merged[-1] in ("$", "(", "($")):
            merged[-1] = merged[-1] + c
        else:
            merged.append(c)
    return " | ".join(merged)


def html_to_text(raw: str) -> str:
    return html_title_and_text(raw)[1]


def html_title_and_text(raw: str) -> tuple[str | None, str]:
    """The <title> (whitespace collapsed, None if absent or empty) and the text, in one linear parse."""
    p = _Extractor()
    p.feed(raw)
    p.close()
    title = " ".join("".join(p.title or ()).split()) or None
    text = html.unescape("".join(p.parts)).replace("\xa0", " ")
    lines = [" ".join(line.split()) for line in text.splitlines()]
    out: list[str] = []
    for line in lines:
        if line or (out and out[-1]):
            out.append(line)
    return title, re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()
