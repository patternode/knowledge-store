"""CSV and TSV rows for an unmapped file.

A mapped table is bound later and never refined. A file no mapping names is still
prose, so each data row becomes one line and carries its column name. A passage can
then keep a row whole. The first row is the header.

A column named title wins over one named name. A repeated header gets a distinct
label. A cell that contains the row separator is written with a slash, so a later
split stays on the real cell boundary.
"""

from __future__ import annotations

import csv
import io

_SEPARATOR = " | "
_TITLE = ("title", "name")


def table_text(text: str, *, tab: bool) -> tuple[str, str | None]:
    """The rows as ``column: value | column: value``, and a title when a column is named one."""
    reader = csv.reader(io.StringIO(text, newline=""), csv.excel_tab if tab else csv.excel)
    raw = list(reader)
    if not raw:
        return "", None
    labels, bases = _labels(raw[0])
    lines: list[str] = []
    for record in raw[1:]:
        if not any(cell.strip() for cell in record):
            continue
        pairs = []
        for label, cell in zip(labels, record):
            value = _clean(cell)
            if value:
                pairs.append(f"{label}: {value}")
        used = set(labels)
        number = len(labels) + 1
        for cell in record[len(labels):]:
            value = _clean(cell)
            if not value:
                continue
            while f"column {number}" in used:
                number += 1
            label = f"column {number}"
            used.add(label)
            number += 1
            pairs.append(f"{label}: {value}")
        if pairs:
            lines.append(_SEPARATOR.join(pairs))
    return "\n".join(lines), _pick_title(bases, raw[1:])


def _labels(header: list[str]) -> tuple[list[str], list[str]]:
    seen: dict[str, int] = {}
    used: set[str] = set()
    labels: list[str] = []
    bases: list[str] = []
    for index, cell in enumerate(header):
        base = _clean(cell) or _blank(index, seen, used)
        count = seen.get(base, 0) + 1
        seen[base] = count
        label = base if count == 1 else f"{base} ({count})"
        while label in used:
            count += 1
            seen[base] = count
            label = f"{base} ({count})"
        used.add(label)
        labels.append(label)
        bases.append(base)
    return labels, bases


def _blank(index: int, seen: dict[str, int], used: set[str]) -> str:
    number = index + 1
    while f"column {number}" in seen or f"column {number}" in used:
        number += 1
    return f"column {number}"


def _pick_title(bases: list[str], records: list[list[str]]) -> str | None:
    """The first filled title cell, or else the first filled name cell."""
    for wanted in _TITLE:
        for record in records:
            for base, cell in zip(bases, record):
                if base.lower() == wanted and (value := _clean(cell)):
                    return value[:200]
    return None


def _clean(cell: str) -> str:
    return " ".join(cell.split()).replace(_SEPARATOR, " / ")
