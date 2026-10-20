"""Reading a literal value, the one way extraction, bind and the table tools all read it.

parse_value turns the text a document or a table holds into its Python value: "1,100" and
"$1,200" are numbers, "14 July 2023" is a date. canonical gives that value back as the one text
form it is stored and compared in (1100, 1200, 2023-07-14), so a filter, a total and a citation
check all see the same value whatever way the source wrote it.

Standard library only: the tool Lambdas import it.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal, InvalidOperation


def parse_value(value: str, kind: str):
    """The literal's Python value, or a ValueError naming what is wrong."""
    v = value.strip()
    if kind == "decimal":
        try:
            return Decimal(v.replace(",", "").lstrip("$€£").rstrip("%").strip())
        except InvalidOperation:
            raise ValueError(f"{value!r} is not a number") from None
    if kind == "integer":
        try:
            return int(v.replace(",", "").lstrip("$€£").strip())
        except ValueError:
            raise ValueError(f"{value!r} is not a whole number") from None
    if kind == "date":
        for fmt in ("%Y-%m-%d", "%d %B %Y", "%B %d, %Y", "%d %b %Y", "%b %d, %Y", "%Y"):
            try:
                return dt.datetime.strptime(v, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"{value!r} is not a date (write it as YYYY-MM-DD or as the passage has it)")
    if kind == "boolean":
        if v.lower() in ("true", "yes"):
            return True
        if v.lower() in ("false", "no"):
            return False
        raise ValueError(f"{value!r} is not true or false")
    return v


def canonical(value, kind: str) -> str | None:
    """The stored text form of a value of this kind, or None if it is not one."""
    try:
        v = parse_value(str(value), kind or "string")
    except ValueError:
        return None
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, Decimal):
        if not v.is_finite():
            return None
        text = format(v, "f")
        return (text.rstrip("0").rstrip(".") if "." in text else text) or "0"
    if isinstance(v, dt.date):
        return v.isoformat()
    return str(v)


def number(value, kind: str = "decimal") -> Decimal | None:
    """A value as a Decimal, or None if it is not a number."""
    c = canonical(value, "decimal" if kind not in ("integer", "decimal") else kind)
    try:
        return Decimal(c) if c is not None else None
    except InvalidOperation:
        return None
