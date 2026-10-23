"""Canonical text, before any ontology is involved.

Refine runs this on the parsed text. The bronze bytes stay as they were. The silver
document and its passages are this form, so a date, a time, a time period and a number
are written one way whatever the file called them. The reading of a number and of a
written date is kernel.values, the same reading a table cell uses.

A time period is an ISO 8601 interval (2023-07-14/2023-07-20, 09:00/17:00) or a
duration (PT2H, P3D, P14D/P30D). A month written with its year is that month (2023-07).
Milliseconds are decimal seconds, which is the ISO duration form.

Only forms that are unambiguous are rewritten. A numeric date that could be day-first or
month-first is left as written. A clock without am/pm, a zone, or an hour of 13 or more
(or 00) is left as written, unless it sits against a date or in a range where the other
end fixes the reading. A bare year is not a date. A quarter, a fiscal year and a half
stay as written, because the calendar they use is not fixed. A business day is not a
fixed length. Words such as yes and no are not booleans. A hyphenated range of numbers
is rewritten on each side. Thousands separators are commas and the dedicated group
spaces. Parentheses mark a loss only when the amount has a currency sign or a grouping
separator. Quotes, dashes, ellipsis and ligatures fold to ASCII. A link's scheme
and host, an email's domain and a UUID are written in one case. An exact fraction
and a scientific number use the same decimal form as any other number. An
information size is a number and a symbol (8 MB, 10 MiB, 256 B). The B is
uppercase, or the word is byte. A lowercase b stays, so a bit form stays. A bare
B on its own stays, because it also means a billion. A hyphenated tag stays.
Decimal and binary prefixes are not converted into each other. Fenced code
is left as written. Nothing here is a class, a synonym or a unit from a domain.
"""

from __future__ import annotations

import datetime as dt
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from urllib.parse import urlsplit, urlunsplit

from knowledge_store.kernel.values import canonical

CONFORMER_VERSION = "conform@1"

_EXAMPLES = 3

# Dedicated group spaces are thousands separators. A single one is enough.
# A regular space is a word space, so "1 234 567" and a telephone number stay.
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
# A hyphen and HH:MM is a clock range ("09:15-09:35"), so it is not an offset.
# Offsets are a name, a plus sign, or four digits with no colon ("-0500").
_ZONE = r"(?:\s*(Z|UTC|GMT|[+]\d{2}:?\d{2}|-\d{4}))?"
# No caret: match() is already anchored at the index it is given, and a caret would
# mean the start of the document instead.
_AFTER_DATE = re.compile(rf"(?:\s*,?\s+at\s+|\s*,\s*|\s+){_CLOCK}{_ZONE}\b", re.IGNORECASE)
# A range shares the date: "2026-03-12 09:15-09:35 UTC" is one span. Taking only the
# first clock leaves the zone for a second pass, so the form would not be stable.
_RANGE = re.compile(rf"\s*[-–—]\s*{_CLOCK}{_ZONE}\b", re.IGNORECASE)
_TIME = re.compile(rf"\b{_CLOCK}{_ZONE}\b", re.IGNORECASE)
# A second clock, so a range can be read as one interval. Groups stay in fives.
# The colon lookbehind keeps a span from starting on the seconds of "10:22:00".
_CLOCK_SPAN = re.compile(
    rf"(?<!:)\b{_CLOCK}{_ZONE}\s*(?:to|–|—|-)\s*{_CLOCK}{_ZONE}\b", re.IGNORECASE)
# A hyphen is included because quotes and dashes are folded to ASCII before this runs.
# The match is only tried at the end of a date, so the hyphens inside an ISO date stay.
_JOIN = re.compile(r"(?:\s+(?:to|through|until)\s+|\s*[–—-]\s*)", re.IGNORECASE)
_JOIN_AND = re.compile(r"\s+and\s+", re.IGNORECASE)
_PREFIX = re.compile(r"(?<!\w)(between|from)\s+$", re.IGNORECASE)
_MONTH_YEAR = re.compile(
    rf"\b(?P<m>{_MONTH})(?P<dot>\.)?[ \t]+(?P<y>\d{{4}})\b",
    re.IGNORECASE)
_DAY_BEFORE = re.compile(r"\b\d{1,2}(?:st|nd|rd|th)?[ \t]$", re.IGNORECASE)
_SHARED_HEAD = re.compile(
    rf"\b(\d{{1,2}}){_ORD}\s*[-–—]\s*(\d{{1,2}}){_ORD}\s+(?:of\s+)?({_MONTH})\.?,?\s+(\d{{4}})\b",
    re.IGNORECASE)
_SHARED_TAIL = re.compile(
    rf"\b({_MONTH})\.?\s+(\d{{1,2}}){_ORD}\s*[-–—]\s*(\d{{1,2}}){_ORD},?\s+(\d{{4}})\b",
    re.IGNORECASE)
_UNIT = (
    r"milliseconds?|minutes?|mins?|seconds?|secs?|hours?|hrs?|"
    r"months?|years?|weeks?|days?|ms")
_QTY = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
_DUR_RANGE = re.compile(
    rf"(?<![\w.$€£¥\-−–])(?P<a>{_QTY})\s*(?:to|–|—|-)\s*(?P<b>{_QTY})\s*-?\s*(?P<u>{_UNIT})\b",
    re.IGNORECASE)
_DUR_LEAD = re.compile(
    rf"(?<![\w.$€£¥\-−–])(?P<q>{_QTY})\s*-?\s*(?P<u>{_UNIT})\b",
    re.IGNORECASE)
_DUR_ATOM = re.compile(rf"(?P<q>{_QTY})\s*-?\s*(?P<u>{_UNIT})\b", re.IGNORECASE)
_DUR_GAP = re.compile(r"\s*,?\s*(?:and\s+)?", re.IGNORECASE)
_KIND = {
    "ms": (0, "ms"), "millisecond": (0, "ms"), "milliseconds": (0, "ms"),
    "sec": (1, "S"), "secs": (1, "S"), "second": (1, "S"), "seconds": (1, "S"),
    "min": (2, "M"), "mins": (2, "M"), "minute": (2, "M"), "minutes": (2, "M"),
    "hr": (3, "H"), "hrs": (3, "H"), "hour": (3, "H"), "hours": (3, "H"),
    "day": (4, "D"), "days": (4, "D"),
    "week": (5, "W"), "weeks": (5, "W"),
    "month": (6, "Mo"), "months": (6, "Mo"),
    "year": (7, "Y"), "years": (7, "Y"),
}
_LONG = {name.lower() for name in _LONG_MONTHS}
_NUMBER = re.compile(
    r"(?<![\w.])(?:(?P<open>\()\s*)?(?P<sign>[-−–]\s*)?(?P<cur>[$€£¥]\s*)?"
    r"(?P<body>\d{1,3}(?:[,\u00a0\u202f\u2009\u2007]\d{3})+(?:\.\d+)?"
    r"|\d+\.\d+|\d+)"
    r"(?:\s*(?P<pct>%|percent|per\s+cent))?(?:\s*(?P<close>\)))?(?![\w])(?!\.\d)",
    re.IGNORECASE)
_FENCE = re.compile(r"```.*?```", re.DOTALL)
_QUOTES = {
    "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'",
    "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u201f": '"',
}
_DASHES = {
    "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-", "\u2014": "-",
    "\u2015": "-", "\u2212": "-",
}
_LIGATURES = {"\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl", "\ufb03": "ffi", "\ufb04": "ffl"}
# Terminating decimals only. A third and a sixth do not have one exact decimal.
_FRAC = {
    "½": "0.5", "¼": "0.25", "¾": "0.75",
    "⅕": "0.2", "⅖": "0.4", "⅗": "0.6", "⅘": "0.8",
    "⅛": "0.125", "⅜": "0.375", "⅝": "0.625", "⅞": "0.875",
}
# A decimal mantissa, or an integer with a signed exponent. "550e8400" is a UUID piece.
_SCI = re.compile(
    r"(?<![\w.])(?:(\d+\.\d+)[eE]([+-]?\d+)|(\d+)[eE]([+-]\d+))(?![\w])")
_URL = re.compile(r"https?://[^\s<>\[\]\"']+", re.IGNORECASE)
_EMAIL = re.compile(
    r"(?<![\w.+-])([\w.+-]+)@((?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,})\b")
_UUID = re.compile(
    r"(?<![\w-])((?:urn:uuid:)?)(\{?)([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})(\}?)(?![\w-])",
    re.IGNORECASE)
# Uppercase B is bytes. A lowercase b is a bit form ("100Gb", "100 Mbps").
# A bare B is also a billion ("70B"), so it is only read inside a range whose
# other side names a real unit ("512B-8MB"). A hyphen before the number is a
# tag ("A100-40GB", "UTF-8 bytes"), not a quantity.
_SIZE_UNIT = r"(?:[Bb]ytes?|[kK]iB|[KMGTPE]iB|[KMGTPE]IB|[kK]B|MB|GB|TB|PB|EB)"
_SIZE_RANGE = re.compile(
    rf"(?<![\w.-])(?P<a>{_QTY})(?:\s*(?P<ua>{_SIZE_UNIT}|B))?\s*-\s*"
    rf"(?P<b>{_QTY})\s*(?P<ub>{_SIZE_UNIT}|B)\b")
_SIZE = re.compile(
    rf"(?<![\w.-])(?P<num>{_QTY})\s*(?P<unit>{_SIZE_UNIT})\b")

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


def _note(counts: Counter, examples: dict[str, list], rule: str, example: str) -> None:
    counts[rule] += 1
    examples.setdefault(rule, [])
    if len(examples[rule]) < _EXAMPLES and example not in examples[rule]:
        examples[rule].append(example)


def _literals(text: str) -> tuple[str, list[tuple[int, int, str, str, str]]]:
    text, notes = _punctuation(text)
    found: list[tuple[int, int, str, str, str]] = []
    _identifiers(text, found)
    _scientific(text, found)
    _durations(text, found)
    _intervals(text, found, _date_starts(text), _point_at)
    _shared_days(text, found)
    for m in _DATE.finditer(text):
        if _overlaps(m.start(), m.end(), found):
            continue
        iso = _date(m)
        if iso is None:
            continue
        new, end = _attach(text, m.end(), iso)
        _keep(found, m.start(), end, text[m.start():end], new)
    for m in _NUMDATE.finditer(text):
        if _overlaps(m.start(), m.end(), found):
            continue
        iso = _numeric_date(m.group(1), m.group(3), m.group(4))
        if iso is None:
            continue
        new, end = _attach(text, m.end(), iso)
        _keep(found, m.start(), end, text[m.start():end], new)
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
        _keep(found, m.start(), end, text[m.start():end], new)
    _intervals(text, found, [m.start() for m in _MONTH_YEAR.finditer(text)], _month_at)
    for m in _MONTH_YEAR.finditer(text):
        if _overlaps(m.start(), m.end(), found):
            continue
        parsed = _month_at(text, m.start())
        if parsed is None:
            continue
        iso, end = parsed
        _keep(found, m.start(), end, text[m.start():end], iso, "period")
    for m in _CLOCK_SPAN.finditer(text):
        if _overlaps(m.start(), m.end(), found):
            continue
        new = _clock_span(m)
        if new and new != m.group():
            _keep(found, m.start(), m.end(), m.group(), new)
        else:
            # Hold the whole range. Rewriting only the end that carries am/pm
            # would leave a 24-hour range for the next pass.
            found.append((m.start(), m.end(), m.group(), m.group(), "period"))
    for m in _TIME.finditer(text):
        if _overlaps(m.start(), m.end(), found):
            continue
        new = _clock(m, attached=False)
        if new and new != m.group():
            found.append((m.start(), m.end(), m.group(), new, "time"))
    _sizes(text, found)
    for m in _NUMBER.finditer(text):
        if _overlaps(m.start(), m.end(), found):
            continue
        new = _number(m)
        if new and new != m.group():
            found.append((m.start(), m.end(), m.group(), new, "number"))
    found.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    parts, at = [], 0
    kept = []
    for start, end, old, new, rule in found:
        if start < at:
            continue
        parts.append(text[at:start])
        parts.append(new)
        at = end
        if new != old:
            kept.append((start, end, old, new, rule))
    parts.append(text[at:])
    return "".join(parts), notes + kept


def _overlaps(start: int, end: int, found: list[tuple[int, int, str, str, str]]) -> bool:
    return any(start < have_end and end > have_start for have_start, have_end, *_ in found)


def _dropped_char(ch: str) -> bool:
    if ch in "\t\n":
        return False
    category = unicodedata.category(ch)
    if category in ("Cc", "Cs"):
        return True
    code = ord(ch)
    return 0xFDD0 <= code <= 0xFDEF or (code & 0xFFFE) == 0xFFFE


def _attach(text: str, end: int, iso: str) -> tuple[str, int]:
    after = _AFTER_DATE.match(text, end)
    if after is None:
        return iso, end
    clock = _clock(after, attached=True)
    if not clock:
        return iso, end
    end = after.end()
    ranged = _RANGE.match(text, end)
    if ranged is not None:
        other = _clock(ranged, attached=True)
        if other:
            clock, other = _share_zone(clock, other)
            return f"{iso}T{clock}/{iso}T{other}", ranged.end()
    return f"{iso}T{clock}", end


def _keep(found: list, start: int, end: int, old: str, new: str, rule: str = "date") -> None:
    if new and new != old and not _overlaps(start, end, found):
        if "/" in new:
            rule = "period"
        found.append((start, end, old, new, rule))


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


def _clock(m: re.Match, *, attached: bool, offset: int = 0) -> str | None:
    def group(index: int) -> str | None:
        return m.group(offset + index)

    hour, minute = int(group(1)), int(group(2))
    second = int(group(3)) if group(3) else None
    ampm = (group(4) or "").lower().replace(".", "").strip()
    zone = _zone(group(5))
    if ampm:
        if not 1 <= hour <= 12:
            return None
        if ampm.startswith("a"):
            hour = 0 if hour == 12 else hour
        else:
            hour = hour if hour == 12 else hour + 12
    elif not 0 <= hour <= 23:
        return None
    elif not attached and zone == "" and hour < 13 and not (hour == 0 and len(group(1) or "") == 2):
        return None
    if zone is None:
        return None
    text = f"{hour:02d}:{minute:02d}"
    if second is not None:
        text += f":{second:02d}"
    return text + zone


def _share_zone(clock: str, other: str) -> tuple[str, str]:
    left, right = _zone_suffix(clock), _zone_suffix(other)
    if right and not left:
        clock += right
    elif left and not right:
        other += left
    return clock, other


def _zone_suffix(value: str) -> str:
    matched = re.search(r"(Z|[+-]\d{2}:\d{2})$", value)
    return matched.group(1) if matched else ""


def _clock_span(m: re.Match) -> str | None:
    # "15:22:00-07:00" is an offset already written in canonical form. The hyphen
    # is glued and only the left clock has seconds.
    if m.group(3) and not m.group(8) and re.search(r"\d-\d", m.group()):
        return None
    left_zone, right_zone = m.group(5), m.group(10)
    # A zone written once on a range applies to both clocks.
    if left_zone and not right_zone:
        right_zone = left_zone
    elif right_zone and not left_zone:
        left_zone = right_zone
    left = _clock(_zoned(m, 0, left_zone), attached=False)
    right = _clock(_zoned(m, 5, right_zone), attached=False)
    hours = (int(m.group(1)), int(m.group(6)))
    forced = bool(left_zone or right_zone) or any(
        hour >= 13 or (hour == 0 and len(m.group(index)) == 2)
        for hour, index in zip(hours, (1, 6)))
    if (left is None or right is None) and forced:
        left = _clock(_zoned(m, 0, left_zone), attached=True)
        right = _clock(_zoned(m, 5, right_zone), attached=True)
    if not left or not right:
        return None
    return f"{left}/{right}"


class _zoned:
    """A match whose zone group is the one the range shares."""

    def __init__(self, match: re.Match, offset: int, zone: str | None):
        self.match = match
        self.offset = offset
        self.zone = zone

    def group(self, index: int) -> str | None:
        if index == 5:
            return self.zone
        return self.match.group(self.offset + index)


def _date_starts(text: str) -> list[int]:
    starts = []
    for pattern in (_DATE, _NUMDATE, _ISODATE):
        starts.extend(m.start() for m in pattern.finditer(text))
    return sorted(set(starts))


def _intervals(text: str, found: list, starts: list[int], parse_at) -> None:
    for pos in starts:
        if _overlaps(pos, pos + 1, found):
            continue
        point = parse_at(text, pos)
        if point is None:
            continue
        iso, end = point
        prefix = _PREFIX.search(text[:pos])
        between = bool(prefix and prefix.group(1).lower() == "between")
        start = prefix.start() if prefix else pos
        if prefix and _overlaps(start, pos, found):
            start, between = pos, False
        join = _JOIN.match(text, end)
        if join is None and between:
            join = _JOIN_AND.match(text, end)
        if join is None:
            continue
        other = parse_at(text, join.end())
        if other is None or _overlaps(start, other[1], found):
            continue
        _keep(found, start, other[1], text[start:other[1]], f"{iso}/{other[0]}")


def _point_at(text: str, pos: int) -> tuple[str, int] | None:
    dated = _leading_date(text, pos)
    if dated is None:
        return None
    iso, end = dated
    after = _AFTER_DATE.match(text, end)
    if after is not None:
        clock = _clock(after, attached=True)
        if clock and _RANGE.match(text, after.end()) is None:
            return f"{iso}T{clock}", after.end()
    return iso, end


def _leading_date(text: str, pos: int) -> tuple[str, int] | None:
    written = _DATE.match(text, pos)
    if written is not None:
        iso = _date(written)
        if iso is not None:
            return iso, written.end()
    numeric = _NUMDATE.match(text, pos)
    if numeric is not None:
        iso = _numeric_date(numeric.group(1), numeric.group(3), numeric.group(4))
        if iso is not None:
            return iso, numeric.end()
    iso_match = _ISODATE.match(text, pos)
    if iso_match is not None:
        try:
            iso = dt.date(int(iso_match.group(1)), int(iso_match.group(2)),
                          int(iso_match.group(3))).isoformat()
        except ValueError:
            return None
        return iso, iso_match.end()
    return None


def _month_at(text: str, pos: int) -> tuple[str, int] | None:
    if _DAY_BEFORE.search(text[:pos]):
        return None
    matched = _MONTH_YEAR.match(text, pos)
    if matched is None:
        return None
    name = matched.group("m")
    if matched.group("dot") and name.lower() in _LONG:
        return None
    number = _month_number(name)
    if number is None:
        return None
    return f"{int(matched.group('y')):04d}-{number:02d}", matched.end()


def _month_number(name: str) -> int | None:
    key = "sep" if name.lower().startswith("sept") else name.lower()[:3]
    for index, full in enumerate(_LONG_MONTHS, start=1):
        if full.lower().startswith(key):
            return index
    return None


def _shared_days(text: str, found: list) -> None:
    for matched in _SHARED_HEAD.finditer(text):
        _shared(found, matched, matched.group(1), matched.group(2), matched.group(3), matched.group(4))
    for matched in _SHARED_TAIL.finditer(text):
        _shared(found, matched, matched.group(2), matched.group(3), matched.group(1), matched.group(4))


def _shared(found: list, matched: re.Match, day: str, other: str, month: str, year: str) -> None:
    if _overlaps(matched.start(), matched.end(), found):
        return
    number = _month_number(month)
    if number is None:
        return
    start = _on_calendar(year, number, day)
    end = _on_calendar(year, number, other)
    if start is None or end is None:
        return
    _keep(found, matched.start(), matched.end(), matched.group(), f"{start}/{end}")


def _on_calendar(year: str, month: int, day: str) -> str | None:
    try:
        return dt.date(int(year), month, int(day)).isoformat()
    except ValueError:
        return None


def _punctuation(text: str) -> tuple[str, list]:
    """ASCII quotes, dashes, ellipsis and ligatures, and an exact fraction."""
    notes = []
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch in _QUOTES or ch in _DASHES:
            repl = _QUOTES[ch] if ch in _QUOTES else _DASHES[ch]
            notes.append((0, 0, ch, repl, "punctuation"))
            out.append(repl)
            i += 1
            continue
        if ch == "\u2026":
            notes.append((0, 0, ch, "...", "punctuation"))
            out.append("...")
            i += 1
            continue
        if ch in _LIGATURES:
            repl = _LIGATURES[ch]
            notes.append((0, 0, ch, repl, "punctuation"))
            out.append(repl)
            i += 1
            continue
        if ch in _FRAC:
            j = i
            while j > 0 and text[j - 1].isdigit():
                j -= 1
            if j < i:
                del out[-(i - j):]
            whole = text[j:i] or "0"
            new = canonical(Decimal(whole) + Decimal(_FRAC[ch]), "decimal")
            old = text[j:i + 1]
            if new and new != old:
                notes.append((0, 0, old, new, "number"))
                out.append(new)
            else:
                out.append(old)
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out), notes


def _identifiers(text: str, found: list) -> None:
    for matched in _URL.finditer(text):
        raw = matched.group()
        core = raw
        while core and core[-1] in ".,;:!?":
            core = core[:-1]
        if core.endswith(")") and core.count("(") < core.count(")"):
            core = core[:-1]
        if not core or _overlaps(matched.start(), matched.start() + len(core), found):
            continue
        new = _canon_url(core)
        end = matched.start() + len(core)
        if new and new != core:
            found.append((matched.start(), end, core, new, "link"))
        else:
            found.append((matched.start(), end, core, core, "link"))
    for matched in _EMAIL.finditer(text):
        if _overlaps(matched.start(), matched.end(), found):
            continue
        domain = matched.group(2).lower()
        if domain == matched.group(2):
            continue
        found.append((matched.start(), matched.end(), matched.group(),
                      f"{matched.group(1)}@{domain}", "email"))
    for matched in _UUID.finditer(text):
        if _overlaps(matched.start(), matched.end(), found):
            continue
        prefix, open_, body, close = matched.group(1), matched.group(2), matched.group(3), matched.group(4)
        if open_ and not close or close and not open_:
            body_text = matched.group()
            new = body_text.lower()
        else:
            new = f"{prefix.lower()}{open_}{body.lower()}{close}"
        if new != matched.group():
            found.append((matched.start(), matched.end(), matched.group(), new, "uuid"))
        else:
            found.append((matched.start(), matched.end(), matched.group(), matched.group(), "uuid"))


def _canon_url(raw: str) -> str | None:
    try:
        parts = urlsplit(raw)
    except ValueError:
        return None
    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"} or not parts.hostname:
        return None
    host = parts.hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    try:
        port = parts.port
    except ValueError:
        return None
    netloc = host
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{host}:{port}"
    if parts.username:
        auth = parts.username if parts.password is None else f"{parts.username}:{parts.password}"
        netloc = f"{auth}@{netloc}"
    return urlunsplit((scheme, netloc, parts.path, parts.query, parts.fragment))


def _sizes(text: str, found: list) -> None:
    for matched in _SIZE_RANGE.finditer(text):
        if _overlaps(matched.start(), matched.end(), found):
            continue
        left_unit, right_unit = matched.group("ua"), matched.group("ub")
        if right_unit == "B" and (left_unit is None or left_unit == "B"):
            continue
        left = _size_amount(matched.group("a"), left_unit or right_unit)
        right = _size_amount(matched.group("b"), right_unit)
        if left is None or right is None:
            continue
        new = f"{left}-{right}"
        old = matched.group()
        found.append((matched.start(), matched.end(), old, new if new != old else old, "size"))
    for matched in _SIZE.finditer(text):
        if _overlaps(matched.start(), matched.end(), found):
            continue
        new = _size_amount(matched.group("num"), matched.group("unit"))
        if new is None:
            continue
        old = matched.group()
        found.append((matched.start(), matched.end(), old, new if new != old else old, "size"))


def _size_amount(num: str, unit: str) -> str | None:
    digits = canonical(num, "decimal")
    if digits is None:
        return None
    return f"{digits} {_size_symbol(unit)}"


def _size_symbol(unit: str) -> str:
    if unit == "B" or unit.lower() in ("byte", "bytes"):
        return "B"
    if len(unit) == 3 and unit[1].lower() == "i":
        return f"{unit[0].upper()}iB"
    return f"{unit[0].upper()}B"


def _scientific(text: str, found: list) -> None:
    for matched in _SCI.finditer(text):
        if _overlaps(matched.start(), matched.end(), found):
            continue
        body = matched.group(1) or matched.group(3)
        exponent = int(matched.group(2) if matched.group(1) else matched.group(4))
        if not -18 <= exponent <= 18:
            continue
        new = canonical(Decimal(body) * (Decimal(10) ** exponent), "decimal")
        if new and new != matched.group():
            found.append((matched.start(), matched.end(), matched.group(), new, "number"))


def _durations(text: str, found: list) -> None:
    for matched in _DUR_RANGE.finditer(text):
        if _overlaps(matched.start(), matched.end(), found):
            continue
        start = _iso_duration([(matched.group("a"), matched.group("u"))])
        end = _iso_duration([(matched.group("b"), matched.group("u"))])
        if start and end:
            _keep(found, matched.start(), matched.end(), matched.group(), f"{start}/{end}", "period")
    cursor = 0
    while True:
        matched = _DUR_LEAD.search(text, cursor)
        if matched is None:
            return
        if _overlaps(matched.start(), matched.end(), found):
            cursor = matched.end()
            continue
        parts = [(matched.group("q"), matched.group("u"))]
        end = matched.end()
        while True:
            gap = _DUR_GAP.match(text, end)
            if gap is None or gap.end() == end:
                break
            nxt = _DUR_ATOM.match(text, gap.end())
            if nxt is None:
                break
            rank = _KIND.get(nxt.group("u").lower())
            previous = _KIND.get(parts[-1][1].lower())
            if rank is None or previous is None or rank[0] >= previous[0]:
                # "2 hours 1 day" is out of order, so neither part is rewritten.
                if rank is not None and previous is not None and rank[0] > previous[0]:
                    parts = []
                    end = nxt.end()
                break
            parts.append((nxt.group("q"), nxt.group("u")))
            end = nxt.end()
        iso = _iso_duration(parts) if parts else None
        if iso:
            _keep(found, matched.start(), end, text[matched.start():end], iso, "period")
        cursor = end


def _iso_duration(parts: list[tuple[str, str]]) -> str | None:
    kinds = []
    for raw, unit in parts:
        qty = canonical(raw, "decimal")
        kind = _KIND.get(unit.lower())
        if qty is None or kind is None:
            return None
        kinds.append((kind[0], kind[1], qty))
    if any(kind == "W" for _, kind, _ in kinds) and len(kinds) != 1:
        return None
    if len(kinds) == 1 and kinds[0][1] == "W":
        return f"P{kinds[0][2]}W"
    ranks = [rank for rank, _, _ in kinds]
    if ranks != sorted(ranks, reverse=True) or len(ranks) != len(set(ranks)):
        return None
    date, time = [], []
    seconds: Decimal | None = None
    for _, kind, qty in kinds:
        if kind == "ms":
            seconds = (seconds or Decimal(0)) + Decimal(qty) / Decimal(1000)
            continue
        if kind == "S":
            seconds = (seconds or Decimal(0)) + Decimal(qty)
            continue
        designator = "M" if kind == "Mo" else kind
        (date if kind in ("Y", "Mo", "D") else time).append(f"{qty}{designator}")
    if seconds is not None:
        text = canonical(seconds, "decimal")
        if text is None:
            return None
        time.append(f"{text}S")
    if not date and not time:
        return None
    written = "P" + "".join(date)
    if time:
        written += "T" + "".join(time)
    return written


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
    open_, close = m.group("open"), m.group("close")
    if (open_ is None) != (close is None):
        return None
    sign = (m.group("sign") or "").strip()
    cur = (m.group("cur") or "").strip()
    pct = m.group("pct")
    # "(1.4)" and "(0.5%)" are parentheticals. A loss needs a currency sign or a
    # thousands separator, as in "($1,200)" and "(1,200)".
    grouped = "," in body or any(ch in body for ch in _GROUP_SPACES)
    if open_ and not (grouped or cur):
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
    if any(ch in body for ch in f",{_GROUP_SPACES}"):
        return True
    # An empty sign is a substring of every string, so membership has to be a real character.
    if sign in ("−", "–"):
        return True
    if pct == "%" and built != m.group():
        return True
    if "." in body:
        return canonical(compact, "decimal") not in (None, compact)
    return False
