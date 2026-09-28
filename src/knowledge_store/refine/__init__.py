"""Refine: bronze bytes -> silver documents and passages.

A parser is chosen by extension, then by content type. Each parser has a version; the
silver document records it, so a parser change is visible and a reparse can be targeted.
Parsers for binary formats with optional dependencies (pypdf) fail softly: the document is
recorded as unparsed with the reason, and nothing downstream sees it.
"""

from __future__ import annotations

from .parsers import PARSERS, ParseResult, UnsupportedFormat, parse

__all__ = ["PARSERS", "ParseResult", "UnsupportedFormat", "parse"]
