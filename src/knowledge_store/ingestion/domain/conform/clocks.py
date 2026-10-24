"""Clocks and clock ranges."""

from __future__ import annotations

import re

from knowledge_store.ingestion.domain.conform.log import _keep, _overlaps

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


def _claim_clocks(text: str, found: list) -> None:
    for matched in _CLOCK_SPAN.finditer(text):
        if _overlaps(matched.start(), matched.end(), found):
            continue
        new = _clock_span(matched)
        if new and new != matched.group():
            _keep(found, matched.start(), matched.end(), matched.group(), new)
        else:
            # Hold the whole range. Rewriting only the end that carries am/pm
            # would leave a 24-hour range for the next pass.
            found.append((matched.start(), matched.end(), matched.group(), matched.group(), "period"))
    for matched in _TIME.finditer(text):
        if _overlaps(matched.start(), matched.end(), found):
            continue
        new = _clock(matched, attached=False)
        if new and new != matched.group():
            found.append((matched.start(), matched.end(), matched.group(), new, "time"))
