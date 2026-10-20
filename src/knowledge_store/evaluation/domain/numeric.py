"""Numbers in an answer, and whether one of them is the expected figure.

An answer states a figure at some rounding: "$2.2 billion" is 2,200,000,000 stated to the
hundred million. The figure matches when the expected value rounds to what the answer states,
that is, when they differ by at most half a unit of the answer's last stated digit. The rounding
is the answer's, never the expected value's: a round expected figure (3,000,000,000) must not
widen the window for every number near it. A set can instead give a relative tolerance.

Only numbers the answer states count; a year (four digits, no scale, no decimals, 1900 to 2100)
is never taken for a figure.
"""

from __future__ import annotations

import re
from decimal import Decimal

SCALES = {"thousand": 3, "k": 3, "million": 6, "mn": 6, "m": 6, "billion": 9, "bn": 9, "b": 9, "trillion": 12, "tn": 12}
NUMBER = re.compile(r"(?<![\w.])(-|\()?\$?(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?\s*(%|thousand|million|billion|trillion|bn|mn|tn|[kmb]\b)?",
                    re.IGNORECASE)


def stated(text: str) -> list[tuple[Decimal, Decimal]]:
    """Every number the text states, as (value, half a unit of its last stated digit)."""
    out = []
    for m in NUMBER.finditer(text or ""):
        sign, whole, frac, scale = m.group(1), m.group(2).replace(",", ""), m.group(3) or "", (m.group(4) or "").lower()
        if not scale and not frac and len(whole) == 4 and 1900 <= int(whole) <= 2100:
            continue
        digits = Decimal(whole + frac)
        exp = SCALES.get(scale, 0)
        value = digits.scaleb(exp)
        places = len(frac) - 1 if frac else 0
        half = Decimal(5).scaleb(exp - places - 1)
        out.append((-value if sign else value, half))
    return out


def matches(text: str, expected: float, tolerance: float | None = None) -> bool:
    """The text states the expected figure."""
    target = Decimal(str(expected))
    for value, half in stated(text):
        if tolerance is not None:
            if abs(value - target) <= abs(target) * Decimal(str(tolerance)):
                return True
        elif abs(value - target) <= half:
            return True
    return False
