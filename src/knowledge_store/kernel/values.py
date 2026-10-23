"""Reading a literal value, the one way extraction, bind and the table tools all read it.

parse_value turns the text a document or a table holds into its Python value: "1,100" and
"$1,200" are numbers, "14 July 2023" is a date. canonical gives that value back as the one text
form it is stored and compared in (1100, 1200, 2023-07-14), so a filter, a total and a citation
check all see the same value whatever way the source wrote it.

Standard library only: the tool Lambdas import it.
"""

from __future__ import annotations

import datetime as dt
import re
from decimal import Decimal, InvalidOperation

_DURATION = re.compile(
    r"^P(?:(?P<Y>\d+(?:\.\d+)?)Y)?(?:(?P<Mo>\d+(?:\.\d+)?)M)?(?:(?P<W>\d+(?:\.\d+)?)W)?"
    r"(?:(?P<D>\d+(?:\.\d+)?)D)?(?:T(?:(?P<H>\d+(?:\.\d+)?)H)?(?:(?P<M>\d+(?:\.\d+)?)M)?"
    r"(?:(?P<S>\d+(?:\.\d+)?)S)?)?$")
_MONTH = re.compile(r"^\d{4}-(?P<m>\d{2})$")
_CLOCK = re.compile(r"^(?P<h>\d{2}):(?P<n>\d{2})(?::(?P<s>\d{2}))?(?P<z>Z|[+-]\d{2}:\d{2})?$")


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
    if kind == "dateTime":
        return _date_time(v)
    if kind == "duration":
        return _duration(v)
    if kind == "interval":
        return _interval(v)
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
    if isinstance(v, dt.datetime):
        return _write_date_time(v)
    if isinstance(v, dt.date):
        return v.isoformat()
    return str(v)


def _date_time(value: str) -> dt.datetime:
    if "T" not in value:
        raise ValueError(f"{value!r} is not a date and time (write it as YYYY-MM-DDThh:mm)")
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        raise ValueError(f"{value!r} is not a date and time (write it as YYYY-MM-DDThh:mm)") from None
    if parsed.tzinfo is None:
        return parsed
    return parsed


def _write_date_time(value: dt.datetime) -> str:
    zone = ""
    if value.tzinfo is not None:
        if value.utcoffset() == dt.timedelta(0):
            zone = "Z"
        else:
            zone = value.isoformat()[-6:]
        value = value.replace(tzinfo=None)
    text = value.isoformat()
    if value.second == 0 and value.microsecond == 0 and text.endswith(":00"):
        text = text[:-3]
    return text + zone


def _duration(value: str) -> str:
    matched = _DURATION.fullmatch(value)
    if matched is None:
        raise ValueError(f"{value!r} is not an ISO 8601 duration (write it as PT2H or P3D)")
    parts = matched.groupdict()
    if not any(parts.values()):
        raise ValueError(f"{value!r} is not an ISO 8601 duration (write it as PT2H or P3D)")
    if parts["W"] and any(parts[name] for name in ("Y", "Mo", "D", "H", "M", "S")):
        raise ValueError(f"{value!r} mixes a week with another unit")
    if "T" in value and not any(parts[name] for name in ("H", "M", "S")):
        raise ValueError(f"{value!r} has no time part after T")
    if parts["W"]:
        return f"P{_amount(parts['W'])}W"
    date = [(name, designator) for name, designator in (("Y", "Y"), ("Mo", "M"), ("D", "D")) if parts[name]]
    time = [(name, designator) for name, designator in (("H", "H"), ("M", "M"), ("S", "S")) if parts[name]]
    written = "P" + "".join(f"{_amount(parts[name])}{designator}" for name, designator in date)
    if time:
        written += "T" + "".join(f"{_amount(parts[name])}{designator}" for name, designator in time)
    return written


def _amount(raw: str) -> str:
    text = canonical(raw, "decimal")
    if text is None:
        raise ValueError(f"{raw!r} is not a number")
    return text


def _interval(value: str) -> str:
    if value.count("/") != 1:
        raise ValueError(f"{value!r} is not an interval (write it as start/end)")
    left, right = value.split("/")
    return f"{_side(left)}/{_side(right)}"


def _side(value: str) -> str:
    text = value.strip()
    if text.startswith("P"):
        return _duration(text)
    if "T" in text:
        return _write_date_time(_date_time(text))
    month = _MONTH.fullmatch(text)
    if month is not None:
        if not 1 <= int(month.group("m")) <= 12:
            raise ValueError(f"{value!r} is not a month")
        return text
    clock = _CLOCK.fullmatch(text)
    if clock is not None:
        hour, minute = int(clock.group("h")), int(clock.group("n"))
        second = clock.group("s")
        if hour > 23 or minute > 59 or (second is not None and int(second) > 59):
            raise ValueError(f"{value!r} is not a clock")
        body = f"{hour:02d}:{minute:02d}"
        if second is not None and second != "00":
            body += f":{second}"
        return body + (clock.group("z") or "")
    written = canonical(text, "date")
    if written is None:
        raise ValueError(f"{value!r} is not a date, a time or a duration")
    return written


def number(value, kind: str = "decimal") -> Decimal | None:
    """A value as a Decimal, or None if it is not a number."""
    c = canonical(value, "decimal" if kind not in ("integer", "decimal") else kind)
    try:
        return Decimal(c) if c is not None else None
    except InvalidOperation:
        return None
