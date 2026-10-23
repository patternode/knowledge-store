"""Information sizes: a number and a symbol, with each prefix family left as itself."""

from __future__ import annotations

import re

from knowledge_store.kernel.values import canonical
from knowledge_store.ingestion.domain.conform.log import _overlaps
from knowledge_store.ingestion.domain.conform.numbers import _QTY

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
