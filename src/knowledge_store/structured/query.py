"""lookup_rows, aggregate and describe_structured, over a bound snapshot.

Filters are an attribute, an operator and a value. A named metric is recomputed from its
SELECT against the snapshot; the SELECT itself is not executed as SQL. An ad hoc aggregate
is count, sum, min, max or avg, with one group-by. Nothing here accepts a query string.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation

from ..store import Store
from .bind import active, binding, published_mapping
from .mapping import Mapping, Table

OPS = ("eq", "neq", "lt", "lte", "gt", "gte", "prefix")
AGG = ("count", "sum", "min", "max", "avg")
ROW_CAP = 40
_SELECT = re.compile(
    r"^SELECT\s+(COUNT\(\*\)|(SUM|MIN|MAX|AVG)\((\w+)\))\s+FROM\s+(\w+)(?:\s+WHERE\s+(.+))?$",
    re.IGNORECASE)
_CMP = re.compile(r"^(\w+)\s*(=|<>|!=|<=|>=|<|>)\s*(?:'([^']*)'|(-?\d+(?:\.\d+)?))$")


def _cells(lake: Store, version: str | None = None) -> list[dict]:
    rows = []
    for entry in binding(lake, version).values():
        key = entry.get("cells")
        if key and lake.exists(key):
            for line in lake.get(key).decode().splitlines():
                if line.strip():
                    rows.append(json.loads(line))
    return rows


def _visible(cell: dict, private: bool) -> bool:
    return private or cell.get("scope", "public") == "public"


def _column(table: Table, name: str):
    return table.column(name)


def _cmp(op: str, stored: str, datatype: str, value: str) -> bool:
    if op == "prefix":
        return stored.startswith(value)
    if datatype in ("integer", "decimal"):
        try:
            a, b = Decimal(stored), Decimal(str(value).strip())
        except InvalidOperation:
            return False
        return {"eq": a == b, "neq": a != b, "lt": a < b, "lte": a <= b, "gt": a > b, "gte": a >= b}[op]
    if datatype == "date":
        return {"eq": stored == value, "neq": stored != value, "lt": stored < value, "lte": stored <= value,
                "gt": stored > value, "gte": stored >= value}[op]
    if op == "eq":
        return stored == str(value)
    if op == "neq":
        return stored != str(value)
    return {"lt": stored < str(value), "lte": stored <= str(value), "gt": stored > str(value),
            "gte": stored >= str(value)}[op]


def _groups(cells: list[dict], table: Table) -> dict[str, dict[str, dict]]:
    """key -> column -> cell, for one table's visible cells."""
    out: dict[str, dict[str, dict]] = {}
    for c in cells:
        if c.get("table") != table.logical_table:
            continue
        out.setdefault(c["key"], {})[c["column"]] = c
    return out


def _keep(row: dict[str, dict], table: Table, filters: list[dict]) -> bool:
    for f in filters:
        col = _column(table, str(f.get("attribute") or f.get("column") or ""))
        if col is None:
            return False
        cell = row.get(col.name)
        if cell is None:
            return False
        op = str(f.get("op") or "eq")
        if op not in OPS:
            return False
        if not _cmp(op, cell["value"], col.datatype or cell.get("datatype") or "string", str(f.get("value") if f.get("value") is not None else "")):
            return False
    return True


def _cell_view(cell: dict, cells: list[dict]) -> dict:
    """One cell, plus the other cells of its row, in file order. The row is what a citation shows."""
    keys = ("cell", "table", "key", "column", "value", "datatype", "snapshot", "class", "attribute")
    row = [{"column": s["column"], "value": s["value"], "cell": s["cell"]}
           for s in cells
           if s["table"] == cell["table"] and s["key"] == cell["key"] and s["snapshot"] == cell["snapshot"]]
    return {**{k: cell[k] for k in keys}, "row": row}


def _row(table: Table, key: str, cols: dict[str, dict]) -> dict:
    values = {}
    for col in table.columns:
        cell = cols.get(col.name)
        if cell:
            values[col.attribute or col.relation or col.name] = {"value": cell["value"], "cell": cell["cell"]}
    return {"type": table.class_name, "key": key, "values": values}


def describe(lake: Store) -> dict:
    mapping = published_mapping(lake)
    if mapping is None:
        return {"types": [], "metrics": []}
    bound = binding(lake)
    types = []
    for t in mapping.tables:
        b = bound.get(t.logical_table) or {}
        types.append({"type": t.class_name, "logical_table": t.logical_table, "location": t.location,
                      "source": b.get("source"), "snapshot": b.get("snapshot"), "scope": b.get("scope", t.scope),
                      "key": list(t.key), "rows": b.get("rows"),
                      "columns": [c.to_json() for c in t.columns]})
    metrics = []
    for m in mapping.metrics:
        b = bound.get(m.source_table) or {}
        metrics.append({"name": m.name, "description": m.description, "source_table": m.source_table,
                        "snapshot": b.get("snapshot"), "concepts": list(m.concepts)})
    return {"version": active(lake), "types": types, "metrics": metrics}


def lookup_rows(lake: Store, type_name: str, filters: list[dict] | None = None, *, limit: int = ROW_CAP,
                private: bool = False, cell_ids: list[str] | None = None) -> dict:
    mapping = published_mapping(lake)
    if mapping is None:
        return {"error": "this collection has no mapped tables"}
    cells = [c for c in _cells(lake) if _visible(c, private)]
    if cell_ids:
        wanted = set(cell_ids)
        found = [c for c in cells if c["cell"] in wanted]
        return {"cells": [_cell_view(c, cells) for c in found]}
    table = mapping.by_class(type_name) or mapping.table(type_name)
    if table is None:
        return {"error": f"no mapped type {type_name!r}; call describe_structured"}
    bound = binding(lake).get(table.logical_table) or {}
    rows = [_row(table, key, cols) for key, cols in _groups(cells, table).items() if _keep(cols, table, filters or [])]
    cap = max(1, min(int(limit or ROW_CAP), 100))
    return {"type": table.class_name, "logical_table": table.logical_table, "snapshot": bound.get("snapshot"),
            "rows": rows[:cap], "total": len(rows), "truncated": len(rows) > cap}


def _number(value: str, datatype: str):
    if datatype == "integer":
        return int(Decimal(value))
    return Decimal(value)


def _reduce(op: str, values: list[str], datatype: str):
    if op == "count":
        return len(values)
    nums = [_number(v, datatype) for v in values]
    if not nums:
        return None
    if op == "sum":
        return sum(nums)
    if op == "min":
        return min(nums)
    if op == "max":
        return max(nums)
    if op == "avg":
        return sum(nums) / Decimal(len(nums))
    raise ValueError(op)


def _where(expr: str) -> list[dict]:
    filters = []
    for part in re.split(r"\s+AND\s+", expr, flags=re.IGNORECASE):
        m = _CMP.match(part.strip())
        if not m:
            raise ValueError(f"this SELECT's WHERE is not recomputable from the snapshot: {part!r}")
        op = {"=": "eq", "<>": "neq", "!=": "neq", "<": "lt", "<=": "lte", ">": "gt", ">=": "gte"}[m.group(2)]
        filters.append({"attribute": m.group(1), "op": op, "value": m.group(3) if m.group(3) is not None else m.group(4)})
    return filters


def aggregate(lake: Store, *, metric: str = "", type_name: str = "", op: str = "", attribute: str = "",
              group_by: str = "", filters: list[dict] | None = None, private: bool = False,
              snapshot: str = "") -> dict:
    mapping = published_mapping(lake)
    if mapping is None:
        return {"error": "this collection has no mapped tables"}
    if metric:
        m = next((x for x in mapping.metrics if x.name == metric), None)
        if m is None:
            return {"error": f"no metric {metric!r}; call describe_structured"}
        parsed = _SELECT.match(m.expression)
        if not parsed:
            return {"error": f"metric {metric!r} is not recomputable from the snapshot"}
        table = mapping.table(parsed.group(4))
        if table is None or table.logical_table != m.source_table:
            return {"error": f"metric {metric!r} does not read {m.source_table}"}
        kind = "count" if parsed.group(1).upper().startswith("COUNT") else parsed.group(2).lower()
        attr = "" if kind == "count" else parsed.group(3)
        try:
            wh = _where(parsed.group(5)) if parsed.group(5) else []
        except ValueError as e:
            return {"error": str(e)}
        out = _aggregate(lake, mapping, table, kind, attr, "", wh, private, snapshot)
        if "error" in out:
            return out
        if snapshot and out.get("snapshot") != snapshot:
            return {"error": f"snapshot {snapshot} is not the snapshot {metric} is bound to"}
        figure = out["figure"]
        return {"metric": metric, "id": f"m:{metric}/{out['snapshot']}", "figure": figure,
                "snapshot": out["snapshot"], "filters": wh, "type": table.class_name}
    table = mapping.by_class(type_name) or mapping.table(type_name)
    if table is None:
        return {"error": f"no mapped type {type_name!r}"}
    if op not in AGG:
        return {"error": f"op must be one of {', '.join(AGG)}"}
    if op != "count" and not attribute:
        return {"error": f"{op} needs an attribute"}
    if group_by and table.column(group_by) is None:
        return {"error": f"no column {group_by!r}"}
    return _aggregate(lake, mapping, table, op, attribute, group_by, filters or [], private, snapshot)


def _aggregate(lake, mapping: Mapping, table: Table, op: str, attribute: str, group_by: str,
               filters: list[dict], private: bool, snapshot: str) -> dict:
    bound = binding(lake).get(table.logical_table) or {}
    if snapshot and bound.get("snapshot") != snapshot:
        return {"error": f"snapshot {snapshot} is not the active snapshot of {table.logical_table}"}
    col = table.column(attribute) if attribute else None
    if attribute and (col is None or not col.attribute):
        return {"error": f"no attribute {attribute!r} on {table.class_name}"}
    if op != "count" and col.datatype not in ("integer", "decimal"):
        return {"error": f"{op} needs a number, and {attribute} is {col.datatype or 'string'}"}
    cells = [c for c in _cells(lake) if _visible(c, private) and (not snapshot or c.get("snapshot") == snapshot)]
    groups = []
    for key, cols in _groups(cells, table).items():
        if not _keep(cols, table, filters):
            continue
        if group_by:
            gcol = table.column(group_by)
            gcell = cols.get(gcol.name) if gcol else None
            label = gcell["value"] if gcell else ""
        else:
            label = ""
        value = cols.get(col.name)["value"] if col and col.name in cols else None
        groups.append((label, value))
    snap = bound.get("snapshot")
    if group_by:
        buckets: dict[str, list[str]] = {}
        for label, value in groups:
            buckets.setdefault(label, [])
            if value is not None or op == "count":
                buckets[label].append(value if value is not None else "")
        rows = []
        for k, vals in sorted(buckets.items()):
            figure = len(vals) if op == "count" else _figure(_reduce(op, [v for v in vals if v != ""], col.datatype))
            rows.append({"group": k, "figure": figure})
        return {"op": op, "type": table.class_name, "attribute": attribute or None, "group_by": group_by,
                "snapshot": snap, "id": f"m:{op}/{snap}", "groups": rows, "filters": filters}
    values = [v for _, v in groups if v is not None] if op != "count" else [v for _, v in groups]
    figure = len(groups) if op == "count" else _reduce(op, values, col.datatype)
    return {"op": op, "type": table.class_name, "attribute": attribute or None, "snapshot": snap,
            "id": f"m:{op}/{snap}", "figure": _figure(figure), "filters": filters, "rows": len(groups)}


def _figure(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        text = format(value, "f")
        return text.rstrip("0").rstrip(".") if "." in text else text
    return value


def values_equal(stated: str, stored: str, datatype: str) -> bool:
    """A cited value against the cell. Numbers compare as decimals, dates as dates."""
    if datatype in ("integer", "decimal"):
        try:
            return Decimal(str(stated).strip()) == Decimal(str(stored).strip())
        except InvalidOperation:
            return False
    if datatype == "date":
        return str(stated).strip()[:10] == str(stored).strip()[:10]
    return str(stated).strip() == str(stored).strip()
