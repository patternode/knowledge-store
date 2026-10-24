"""Unicode folding. It runs on the whole text, fenced code included."""

from __future__ import annotations

import unicodedata
from collections import Counter

from knowledge_store.ingestion.domain.conform.log import _note

# Dedicated group spaces are thousands separators. A single one is enough.
# A regular space is a word space, so "1 234 567" and a telephone number stay.
_GROUP_SPACES = "\u00a0\u202f\u2009\u2007"

_DROP = {"\u00ad", "\u200b", "\u200c", "\u200d", "\ufeff"}

def _fold(text: str) -> tuple[str, Counter, dict[str, list]]:
    """Newlines, unicode spaces and digits, and the invisible characters a parser leaves.

    The four group spaces stay until numbers have been read, because one of them between
    digits is a thousands separator. Anything left is then an ordinary space.
    """
    counts: Counter = Counter()
    examples: dict[str, list] = {}
    norm = unicodedata.normalize("NFC", text)
    if norm != text:
        _note(counts, examples, "unicode_form", "NFC")
    text = norm
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch == "\r":
            _note(counts, examples, "newline", r"\r" + ("\\n" if i + 1 < n and text[i + 1] == "\n" else ""))
            out.append("\n")
            i += 2 if i + 1 < n and text[i + 1] == "\n" else 1
            continue
        if ch in "\u2028\u2029":
            _note(counts, examples, "newline", repr(ch))
            out.append("\n")
            i += 1
            continue
        if ch in _DROP:
            _note(counts, examples, "invisible", repr(ch))
            i += 1
            continue
        # Tab and newline stay. Other controls, unpaired surrogates and non-characters
        # are not text. Emoji stays. Quote and dash folding is outside fenced code.
        if _dropped_char(ch):
            _note(counts, examples, "control", repr(ch))
            i += 1
            continue
        if ch in _GROUP_SPACES:
            out.append(ch)
            i += 1
            continue
        if unicodedata.category(ch) == "Zs" and ch != " ":
            _note(counts, examples, "unicode_space", repr(ch))
            out.append(" ")
            i += 1
            continue
        if unicodedata.category(ch) == "Nd" and ch not in "0123456789":
            _note(counts, examples, "unicode_digit", ch)
            out.append(str(unicodedata.digit(ch)))
            i += 1
            continue
        out.append(ch)
        i += 1
    raw = "".join(out)
    lines = raw.split("\n")
    stripped = [line.rstrip() for line in lines]
    for before, after in zip(lines, stripped):
        if before != after:
            _note(counts, examples, "trailing_space", "end of line")
    return "\n".join(stripped), counts, examples

def _group_spaces(text: str, counts: Counter, examples: dict[str, list]) -> str:
    if not any(ch in _GROUP_SPACES for ch in text):
        return text
    out: list[str] = []
    for ch in text:
        if ch in _GROUP_SPACES:
            _note(counts, examples, "unicode_space", repr(ch))
            out.append(" ")
        else:
            out.append(ch)
    return "".join(out)

def _dropped_char(ch: str) -> bool:
    if ch in "\t\n":
        return False
    category = unicodedata.category(ch)
    if category in ("Cc", "Cs"):
        return True
    code = ord(ch)
    return 0xFDD0 <= code <= 0xFDEF or (code & 0xFFFE) == 0xFFFE
