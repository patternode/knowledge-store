"""Calendar dates, month-years and date intervals."""

from __future__ import annotations

import datetime as dt
import re

from knowledge_store.kernel.values import canonical
from knowledge_store.ingestion.domain.conform.clocks import _AFTER_DATE, _RANGE, _clock, _share_zone
from knowledge_store.ingestion.domain.conform.log import _keep, _overlaps

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

_LONG = {name.lower() for name in _LONG_MONTHS}

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


def _claim_dates(text: str, found: list) -> None:
    _intervals(text, found, _date_starts(text), _point_at)
    _shared_days(text, found)
    for matched in _DATE.finditer(text):
        if _overlaps(matched.start(), matched.end(), found):
            continue
        iso = _date(matched)
        if iso is None:
            continue
        new, end = _attach(text, matched.end(), iso)
        _keep(found, matched.start(), end, text[matched.start():end], new)
    for matched in _NUMDATE.finditer(text):
        if _overlaps(matched.start(), matched.end(), found):
            continue
        iso = _numeric_date(matched.group(1), matched.group(3), matched.group(4))
        if iso is None:
            continue
        new, end = _attach(text, matched.end(), iso)
        _keep(found, matched.start(), end, text[matched.start():end], new)
    for matched in _ISODATE.finditer(text):
        if _overlaps(matched.start(), matched.end(), found):
            continue
        try:
            iso = dt.date(int(matched.group(1)), int(matched.group(2)), int(matched.group(3))).isoformat()
        except ValueError:
            continue
        new, end = _attach(text, matched.end(), iso)
        if end == matched.end():
            continue
        _keep(found, matched.start(), end, text[matched.start():end], new)
    _intervals(text, found, [matched.start() for matched in _MONTH_YEAR.finditer(text)], _month_at)
    for matched in _MONTH_YEAR.finditer(text):
        if _overlaps(matched.start(), matched.end(), found):
            continue
        parsed = _month_at(text, matched.start())
        if parsed is None:
            continue
        iso, end = parsed
        _keep(found, matched.start(), end, text[matched.start():end], iso, "period")
