"""Scientific values and the grouped-number reading shared with table cells."""

from __future__ import annotations

import re
from decimal import Decimal

from knowledge_store.kernel.values import canonical
from knowledge_store.ingestion.domain.conform.fold import _GROUP_SPACES
from knowledge_store.ingestion.domain.conform.log import _overlaps

_QTY = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"

_NUMBER = re.compile(
    r"(?<![\w.])(?:(?P<open>\()\s*)?(?P<sign>[-−–]\s*)?(?P<cur>[$€£¥]\s*)?"
    r"(?P<body>\d{1,3}(?:[,\u00a0\u202f\u2009\u2007]\d{3})+(?:\.\d+)?"
    r"|\d+\.\d+|\d+)"
    r"(?:\s*(?P<pct>%|percent|per\s+cent))?(?:\s*(?P<close>\)))?(?![\w])(?!\.\d)",
    re.IGNORECASE)

# A decimal mantissa, or an integer with a signed exponent. "550e8400" is a UUID piece.
_SCI = re.compile(
    r"(?<![\w.])(?:(\d+\.\d+)[eE]([+-]?\d+)|(\d+)[eE]([+-]\d+))(?![\w])")

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
    if canonical(compact, "decimal") is None:
        return None
    # The digits stay as written: 0.70 and 3.10 are not rewritten to 0.7 and 3.1, because
    # the second is a version as often as a number, and a trailing zero costs a reader nothing.
    digits = compact
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
    return pct == "%" and built != m.group()


def _claim_numbers(text: str, found: list) -> None:
    for matched in _NUMBER.finditer(text):
        if _overlaps(matched.start(), matched.end(), found):
            continue
        new = _number(matched)
        if new and new != matched.group():
            found.append((matched.start(), matched.end(), matched.group(), new, "number"))
