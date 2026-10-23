"""CSV and TSV rows for an unmapped file.

A mapped table is bound later and never refined. A file no mapping names is still
prose, so each data row becomes one line and carries its column name. A passage can
then keep a row whole. The first row is the header.
"""

from __future__ import annotations

import csv
import io

_TITLE = {"title", "name"}


def table_text(text: str, *, tab: bool) -> tuple[str, str | None]:
    """The rows as ``column: value | column: value``, and a title when a column is named one."""
    reader = csv.reader(io.StringIO(text), csv.excel_tab if tab else csv.excel)
    raw = list(reader)
    if not raw:
        return "", None
    labels = _labels(raw[0])
    lines: list[str] = []
    title = None
    for record in raw[1:]:
        if not any(cell.strip() for cell in record):
            continue
        pairs: list[str] = []
        for label, cell in zip(labels, record):
            value = " ".join(cell.split())
            if not value:
                continue
            pairs.append(f"{label}: {value}")
            if title is None and label.lower() in _TITLE:
                title = value[:200]
        for index, cell in enumerate(record[len(labels):], start=len(labels) + 1):
            value = " ".join(cell.split())
            if value:
                pairs.append(f"column {index}: {value}")
        if pairs:
            lines.append(" | ".join(pairs))
    return "\n".join(lines), title


def _labels(header: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    labels = []
    for index, cell in enumerate(header):
        name = " ".join(cell.split()) or f"column {index + 1}"
        count = seen.get(name, 0) + 1
        seen[name] = count
        labels.append(name if count == 1 else f"{name} ({count})")
    return labels
