"""Durations, written as ISO 8601."""

from __future__ import annotations

import re
from decimal import Decimal

from knowledge_store.kernel.values import canonical
from knowledge_store.ingestion.domain.conform.log import _keep, _overlaps
from knowledge_store.ingestion.domain.conform.numbers import _QTY

_UNIT = (
    r"milliseconds?|minutes?|mins?|seconds?|secs?|hours?|hrs?|"
    r"months?|years?|weeks?|days?|ms")

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
        time.append(f"{canonical(seconds, 'decimal')}S")
    if not date and not time:
        return None
    written = "P" + "".join(date)
    if time:
        written += "T" + "".join(time)
    return written
