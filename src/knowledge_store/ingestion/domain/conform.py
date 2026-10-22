"""Canonical text, before any ontology is involved.

Refine runs this on the parsed text. The bronze bytes stay as they were. The silver
document and its passages are this form, so a date, a time and a number are written one
way whatever the file called them. The reading of a number and of a written date is
kernel.values, the same reading a table cell uses.

Only forms that are unambiguous are rewritten. A numeric date that could be day-first or
month-first is left as written. A clock without am/pm, a zone, or an hour of 13 or more
(or 00) is left as written, unless it sits against a date. A bare year is not a date.
Words such as yes and no are not booleans. A hyphenated range is rewritten on each side.
Nothing here is a class, a synonym or a unit from a domain.
"""

from __future__ import annotations

import datetime as dt
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

from knowledge_store.kernel.values import canonical

CONFORMER_VERSION = "conform@1"

_EXAMPLES = 3

# Spaces that are thousands separators, not word spaces. A single one is enough.
# A regular space needs two groups, so "1 234" stays two numbers.
_GROUP_SPACES = "\u00a0\u202f\u2009\u2007"

_LONG_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August",
                "September", "October", "November", "December")
_SHORT_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Sept",
                 "Oct", "Nov", "Dec")
_MONTH = "|".join(sorted(set(_LONG_MONTHS + _SHORT_MONTHS), key=len, reverse=True))
_ORD = r"(?:st|nd|rd|th)?"
_DATE = re.compile(
    rf"\b(?:(?P<d1>\d{{1,2}}){_ORD}\s+(?:of\s+)?(?P<m1>{_MONTH})\.?,?\s+(?P<y1>\d{{4}})"
    rf"|(?P<m2>{_MONTH})\.?\s+(?P<d2>\d{{1,2}}){_ORD},?\s+(?P<y2>\d{{4}}))\b",
    re.IGNORECASE)
_NUMDATE = re.compile(r"\b(\d{1,2})([/-])(\d{1,2})\2(\d{4})\b")
_ISODATE = re.compile(r"\b(\d{4})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b")
# Groups: hour, minute, second, am/pm, zone. The space before am/pm sits inside that
# group, so a clock does not swallow the space that follows it.
_CLOCK = r"(\d{1,2}):([0-5]\d)(?::([0-5]\d))?(\s*[ap]\.?m\.?)?"
_ZONE = r"(?:\s*(Z|UTC|GMT|[+-]\d{2}:?\d{2}))?"
# No caret: match() is already anchored at the index it is given, and a caret would
# mean the start of the document instead.
_AFTER_DATE = re.compile(rf"(?:\s*,?\s+at\s+|\s*,\s*|\s+){_CLOCK}{_ZONE}\b", re.IGNORECASE)
_TIME = re.compile(rf"\b{_CLOCK}{_ZONE}\b", re.IGNORECASE)
_NUMBER = re.compile(
    r"(?<![\w.])(?:(?P<open>\()\s*)?(?P<sign>[-−–]\s*)?(?P<cur>[$€£¥]\s*)?"
    r"(?P<body>\d{1,3}(?:[ \u00a0\u202f\u2009\u2007]\d{3}){2,}(?:\.\d+)?"
    r"|\d{1,3}(?:[,\u00a0\u202f\u2009\u2007]\d{3})+(?:\.\d+)?"
    r"|\d+\.\d+|\d+)"
    r"(?:\s*(?P<pct>%|percent|per\s+cent))?(?:\s*(?P<close>\)))?(?![\w])(?!\.\d)",
    re.IGNORECASE)
_FENCE = re.compile(r"```.*?```", re.DOTALL)

_DROP = {"\u00ad", "\u200b", "\u200c", "\u200d", "\ufeff"}


@dataclass(frozen=True)
class ConformResult:
    text: str
    rules: tuple[dict, ...]


def conform(text: str) -> ConformResult:
    """The canonical text, and one row per rule that changed something."""
    folded, counts, examples = _fold(text)
    pieces: list[str] = []
    pos = 0
    for fence in _FENCE.finditer(folded):
        if fence.start() > pos:
            piece, found = _literals(folded[pos:fence.start()])
            pieces.append(piece)
            _record(found, counts, examples)
        pieces.append(fence.group())
        pos = fence.end()
    if pos < len(folded):
        piece, found = _literals(folded[pos:])
        pieces.append(piece)
        _record(found, counts, examples)
    joined = _group_spaces("".join(pieces), counts, examples)
    rules = tuple({"rule": name, "applied": counts[name], "examples": examples[name]}
                  for name in sorted(counts) if counts[name])
    return ConformResult(joined, rules)


def _record(found, counts: Counter, examples: dict[str, list]) -> None:
    for _, _, old, new, rule in found:
        shown = f"{old} -> {new}"
        _note(counts, examples, rule, shown)


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


def _note(counts: Counter, examples: dict[str, list], rule: str, example: str) -> None:
    counts[rule] += 1
    examples.setdefault(rule, [])
    if len(examples[rule]) < _EXAMPLES and example not in examples[rule]:
        examples[rule].append(example)


def _literals(text: str) -> tuple[str, list[tuple[int, int, str, str, str]]]:
    found: list[tuple[int, int, str, str, str]] = []
    for m in _DATE.finditer(text):
        iso = _date(m)
        if iso is None:
            continue
        new, end = _attach(text, m.end(), iso)
        old = text[m.start():end]
        if new != old:
            found.append((m.start(), end, old, new, "date"))
    for m in _NUMDATE.finditer(text):
        if _overlaps(m.start(), m.end(), found):
            continue
        iso = _numeric_date(m.group(1), m.group(3), m.group(4))
        if iso is None:
            continue
        new, end = _attach(text, m.end(), iso)
        old = text[m.start():end]
        if new != old:
            found.append((m.start(), end, old, new, "date"))
    for m in _ISODATE.finditer(text):
        if _overlaps(m.start(), m.end(), found):
            continue
        try:
            iso = dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
        except ValueError:
            continue
        new, end = _attach(text, m.end(), iso)
        if end == m.end():
            continue
        old = text[m.start():end]
        if new != old:
            found.append((m.start(), end, old, new, "date"))
    for m in _TIME.finditer(text):
        if _overlaps(m.start(), m.end(), found):
            continue
        new = _clock(m, attached=False)
        if new and new != m.group():
            found.append((m.start(), m.end(), m.group(), new, "time"))
    for m in _NUMBER.finditer(text):
        if _overlaps(m.start(), m.end(), found):
            continue
        new = _number(m)
        if new and new != m.group():
            found.append((m.start(), m.end(), m.group(), new, "number"))
    found.sort(key=lambda item: item[0])
    parts, at = [], 0
    for start, end, _, new, _ in found:
        parts.append(text[at:start])
        parts.append(new)
        at = end
    parts.append(text[at:])
    return "".join(parts), found


def _overlaps(start: int, end: int, found: list[tuple[int, int, str, str, str]]) -> bool:
    return any(start < have_end and end > have_start for have_start, have_end, *_ in found)


def _attach(text: str, end: int, iso: str) -> tuple[str, int]:
    after = _AFTER_DATE.match(text, end)
    if after is None:
        return iso, end
    clock = _clock(after, attached=True)
    if not clock:
        return iso, end
    return f"{iso}T{clock}", after.end()


def _date(m: re.Match) -> str | None:
    if m.group("d1"):
        written = f"{int(m.group('d1'))} {_month(m.group('m1'))} {m.group('y1')}"
    else:
        written = f"{_month(m.group('m2'))} {int(m.group('d2'))}, {m.group('y2')}"
    return canonical(written, "date")


def _month(name: str) -> str:
    key = name.lower()[:3]
    for full in _LONG_MONTHS:
        if full.lower().startswith(key):
            return full
    return name


def _numeric_date(day_or_month: str, month_or_day: str, year: str) -> str | None:
    a, b, y = int(day_or_month), int(month_or_day), int(year)
    if a > 12 and 1 <= b <= 12:
        day, month = a, b
    elif b > 12 and 1 <= a <= 12:
        day, month = b, a
    else:
        return None
    try:
        return dt.date(y, month, day).isoformat()
    except ValueError:
        return None


def _clock(m: re.Match, *, attached: bool) -> str | None:
    hour, minute = int(m.group(1)), int(m.group(2))
    second = int(m.group(3)) if m.group(3) else None
    ampm = (m.group(4) or "").lower().replace(".", "").strip()
    zone = _zone(m.group(5))
    if ampm:
        if not 1 <= hour <= 12:
            return None
        if ampm.startswith("a"):
            hour = 0 if hour == 12 else hour
        else:
            hour = hour if hour == 12 else hour + 12
    elif not 0 <= hour <= 23:
        return None
    elif not attached and zone == "" and hour < 13 and not (hour == 0 and len(m.group(1)) == 2):
        return None
    if zone is None:
        return None
    text = f"{hour:02d}:{minute:02d}"
    if second is not None:
        text += f":{second:02d}"
    return text + zone


def _zone(raw: str | None) -> str | None:
    if not raw:
        return ""
    token = raw.strip().upper()
    if token in ("Z", "UTC", "GMT"):
        return "Z"
    parsed = re.fullmatch(r"([+-])(\d{2}):?(\d{2})", token)
    if not parsed:
        return None
    hh, mm = int(parsed.group(2)), int(parsed.group(3))
    if hh > 14 or mm > 59:
        return None
    return f"{parsed.group(1)}{hh:02d}:{mm:02d}"


def _number(m: re.Match) -> str | None:
    body = m.group("body")
    if " " in body and not re.fullmatch(r"\d{1,3}(?: \d{3}){2,}(?:\.\d+)?", body):
        return None
    open_, close = m.group("open"), m.group("close")
    if (open_ is None) != (close is None):
        return None
    sign = (m.group("sign") or "").strip()
    cur = (m.group("cur") or "").strip()
    pct = m.group("pct")
    if open_ and not ("," in body or "." in body or cur or " " in body
                      or any(ch in body for ch in _GROUP_SPACES)):
        return None
    compact = "".join(ch for ch in body if ch not in f", {_GROUP_SPACES}")
    digits = canonical(compact, "decimal")
    if digits is None:
        return None
    negative = bool(sign) or bool(open_)
    if negative and not digits.startswith("-"):
        digits = "-" + digits
    if cur:
        digits = ("-" + cur + digits[1:]) if digits.startswith("-") else cur + digits
    if pct:
        digits += "%"
    if digits == m.group() or not _worth(body, sign, cur, pct, compact, digits, m):
        return None
    return digits


def _worth(body: str, sign: str, cur: str, pct: str | None, compact: str, built: str,
           m: re.Match) -> bool:
    if cur or m.group("open") or (pct and pct != "%"):
        return True
    if " " in body or any(ch in body for ch in f",{_GROUP_SPACES}"):
        return True
    # An empty sign is a substring of every string, so membership has to be a real character.
    if sign in ("−", "–"):
        return True
    if pct == "%" and built != m.group():
        return True
    if "." in body:
        return canonical(compact, "decimal") not in (None, compact)
    return False
