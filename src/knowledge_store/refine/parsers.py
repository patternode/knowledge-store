"""Format parsers: bytes -> text plus a title.

Tables are kept as rows on one line with " | " between cells (html_text.py), so a passage
never splits a row and a model reads a row as one fact.
"""

from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass, field
from typing import Callable

from .html_text import html_to_text


class UnsupportedFormat(Exception):
    pass


@dataclass(frozen=True)
class ParseResult:
    text: str
    title: str | None
    parser: str
    metadata: dict = field(default_factory=dict)


def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-16"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def _first_line_title(text: str) -> str | None:
    for line in text.splitlines():
        line = line.strip().lstrip("#").strip()
        if line:
            return line[:200]
    return None


def parse_text(data: bytes) -> ParseResult:
    text = _decode(data).replace("\r\n", "\n")
    return ParseResult(text, _first_line_title(text), "text@1")


def parse_markdown(data: bytes) -> ParseResult:
    text = _decode(data).replace("\r\n", "\n")
    m = re.search(r"^#\s+(.+)$", text, re.M)
    return ParseResult(text, m.group(1).strip() if m else _first_line_title(text), "markdown@1")


def parse_html(data: bytes) -> ParseResult:
    raw = _decode(data)
    m = re.search(r"<title[^>]*>(.*?)</title>", raw, re.I | re.S)
    title = " ".join(m.group(1).split()) if m else None
    text = html_to_text(raw)
    return ParseResult(text, title or _first_line_title(text), "html@1")


def parse_json(data: bytes) -> ParseResult:
    """JSON: every string value on its own line, labelled with its path, so a record
    reads as prose. A top-level "title" or "name" is the title."""
    obj = json.loads(_decode(data))
    lines: list[str] = []

    def walk(v, path: str) -> None:
        if isinstance(v, dict):
            for k, x in v.items():
                walk(x, f"{path}.{k}" if path else str(k))
        elif isinstance(v, list):
            for i, x in enumerate(v):
                walk(x, f"{path}[{i}]")
        elif v is not None and str(v).strip():
            lines.append(f"{path}: {v}")

    walk(obj, "")
    title = obj.get("title") or obj.get("name") if isinstance(obj, dict) else None
    return ParseResult("\n".join(lines), str(title) if title else None, "json@1")


def parse_pdf(data: bytes) -> ParseResult:
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise UnsupportedFormat("PDF needs the pypdf package (pip install pypdf)") from e
    reader = PdfReader(io.BytesIO(data))
    pages = [(p.extract_text() or "").strip() for p in reader.pages]
    text = "\n\n".join(p for p in pages if p)
    if not text.strip():
        raise UnsupportedFormat("PDF has no text layer (scanned?); OCR is not built in yet")
    meta_title = (reader.metadata.title if reader.metadata else None) or None
    return ParseResult(text, meta_title or _first_line_title(text), "pdf@1", {"pages": len(pages)})


PARSERS: dict[str, Callable[[bytes], ParseResult]] = {
    ".txt": parse_text, ".text": parse_text, ".csv": parse_text, ".tsv": parse_text, ".log": parse_text,
    ".md": parse_markdown, ".markdown": parse_markdown,
    ".html": parse_html, ".htm": parse_html, ".xhtml": parse_html,
    ".json": parse_json,
    ".pdf": parse_pdf,
}

CONTENT_TYPES = {"text/plain": ".txt", "text/markdown": ".md", "text/html": ".html",
                 "application/json": ".json", "application/pdf": ".pdf", "text/csv": ".csv"}


def parse(data: bytes, ext: str, content_type: str | None = None) -> ParseResult:
    fn = PARSERS.get(ext.lower())
    if fn is None and content_type:
        fn = PARSERS.get(CONTENT_TYPES.get(content_type.split(";")[0].strip().lower(), ""))
    if fn is None:
        raise UnsupportedFormat(f"no parser for {ext or content_type or 'unknown format'}")
    return fn(data)
