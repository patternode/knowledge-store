"""The mapping next to an ontology, and the two renditions publish writes from it.

mappings.yaml names each table, the class it fills, and the columns. metrics.osi.yaml
is the accelerator's OSI v1.0 shape: a named figure whose expression is a read-only
SELECT. A directory with neither file publishes as it always has.

A column becomes an attribute only when a published mapping names it. Publish refuses
a class, attribute, relation, datatype or metric concept the ontology does not have.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..ontology import model

_XSD = {"xsd:string": "string", "xsd:integer": "integer", "xsd:int": "integer", "xsd:long": "integer",
        "xsd:decimal": "decimal", "xsd:double": "decimal", "xsd:float": "decimal", "xsd:date": "date",
        "xsd:boolean": "boolean", "string": "string", "integer": "integer", "decimal": "decimal",
        "date": "date", "boolean": "boolean"}
_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SELECT = re.compile(r"^\s*select\b", re.IGNORECASE)
_UNSAFE = re.compile(r"[;]|--|/\*|\b(insert|update|delete|drop|alter|create|grant|copy|call)\b", re.IGNORECASE)


@dataclass(frozen=True)
class Column:
    name: str
    attribute: str = ""
    relation: str = ""
    range: str = ""
    match: str = ""
    datatype: str = ""          # the attribute's kind: string, integer, decimal, date, boolean

    def to_json(self) -> dict:
        out = {"name": self.name}
        if self.attribute:
            out["attribute"] = self.attribute
            out["datatype"] = self.datatype or "string"
        if self.relation:
            out["relation"] = self.relation
            out["range"] = self.range
            out["match"] = self.match
        return out


@dataclass(frozen=True)
class Table:
    name: str
    location: str
    logical_table: str
    class_name: str
    key: tuple[str, ...]
    columns: tuple[Column, ...]
    scope: str = "public"

    def column(self, name: str) -> Column | None:
        return next((c for c in self.columns if c.name == name or c.attribute == name), None)

    def to_json(self) -> dict:
        return {"name": self.name, "location": self.location, "logical_table": self.logical_table,
                "class": self.class_name, "key": list(self.key), "scope": self.scope,
                "columns": [c.to_json() for c in self.columns]}


@dataclass(frozen=True)
class Metric:
    name: str
    description: str
    expression: str
    source_table: str
    concepts: tuple[str, ...] = ()
    unit: str = ""
    return_type: str = ""

    def to_json(self) -> dict:
        return {"name": self.name, "description": self.description, "expression": self.expression,
                "source_table": self.source_table, "concepts": list(self.concepts),
                "unit": self.unit, "return_type": self.return_type}


@dataclass(frozen=True)
class Mapping:
    tables: tuple[Table, ...] = ()
    metrics: tuple[Metric, ...] = ()

    def table(self, name: str) -> Table | None:
        return next((t for t in self.tables if t.logical_table == name or t.class_name == name or t.name == name), None)

    def by_class(self, cls: str) -> Table | None:
        return next((t for t in self.tables if t.class_name == cls), None)

    def locations(self) -> set[str]:
        """File paths the mapping names. A live source (coa:...) is not a file to skip."""
        return {t.location for t in self.tables if t.location and not t.location.startswith("coa:")}

    def to_json(self) -> dict:
        return {"tables": [t.to_json() for t in self.tables], "metrics": [m.to_json() for m in self.metrics]}

    @staticmethod
    def from_json(data: dict) -> "Mapping":
        tables = []
        for t in data.get("tables") or []:
            cols = tuple(Column(name=c["name"], attribute=c.get("attribute") or "", relation=c.get("relation") or "",
                                range=c.get("range") or "", match=c.get("match") or "", datatype=c.get("datatype") or "")
                         for c in t.get("columns") or [])
            tables.append(Table(name=t["name"], location=t.get("location") or "", logical_table=t["logical_table"],
                                class_name=t["class"], key=tuple(t.get("key") or []), columns=cols,
                                scope=t.get("scope") or "public"))
        metrics = tuple(Metric(name=m["name"], description=m.get("description") or "", expression=m.get("expression") or "",
                               source_table=m.get("source_table") or "", concepts=tuple(m.get("concepts") or []),
                               unit=m.get("unit") or "", return_type=m.get("return_type") or "")
                        for m in data.get("metrics") or [])
        return Mapping(tuple(tables), metrics)


def _kind(token: str) -> str:
    t = (token or "").strip()
    if t.startswith("http://www.w3.org/2001/XMLSchema#"):
        t = "xsd:" + t.rsplit("#", 1)[-1]
    if t not in _XSD:
        raise ValueError(f"datatype {token!r} is not one of {', '.join(sorted(set(_XSD.values())))}")
    return _XSD[t]


def _check_select(expression: str, name: str) -> str:
    expr = " ".join((expression or "").split())
    if not expr or not _SELECT.match(expr):
        raise ValueError(f"metric {name!r} expression must be a SELECT")
    if _UNSAFE.search(expr):
        raise ValueError(f"metric {name!r} expression must be one read-only SELECT")
    return expr


def _column(spec: model.OntologySpec, table_class: str, name: str, raw: dict) -> Column:
    if not isinstance(raw, dict):
        raise ValueError(f"column {name!r} must be a mapping of attribute or relation")
    attr, rel = raw.get("attribute") or "", raw.get("relation") or ""
    if bool(attr) == bool(rel):
        raise ValueError(f"column {name!r} names an attribute or a relation, not both and not neither")
    if attr:
        prop = spec.attributes.get(attr)
        if prop is None:
            raise ValueError(f"column {name!r} attribute {attr!r} is not in the ontology")
        if prop.domain and not any(spec.is_a(table_class, d) for d in prop.domain):
            raise ValueError(f"column {name!r} attribute {attr!r} is not of class {table_class}")
        kind = prop.range[0] if prop.range else "string"
        if raw.get("datatype"):
            stated = _kind(str(raw["datatype"]))
            if stated != kind:
                raise ValueError(f"column {name!r} datatype {raw['datatype']} disagrees with {attr}, which is {kind}")
        return Column(name=name, attribute=attr, datatype=kind)
    prop = spec.relations.get(rel)
    if prop is None:
        raise ValueError(f"column {name!r} relation {rel!r} is not in the ontology")
    rng = str(raw.get("range") or (prop.range[0] if len(prop.range) == 1 else ""))
    if not rng or rng not in spec.classes:
        raise ValueError(f"column {name!r} relation {rel!r} needs a range that is a class")
    if prop.range and rng not in prop.range and not any(spec.is_a(rng, r) for r in prop.range):
        raise ValueError(f"column {name!r} range {rng} is not the range of {rel}")
    if prop.domain and not any(spec.is_a(table_class, d) for d in prop.domain):
        raise ValueError(f"column {name!r} relation {rel!r} does not start at {table_class}")
    match = str(raw.get("match") or "")
    if not match:
        raise ValueError(f"column {name!r} relation {rel!r} needs match: the field on {rng} the value equals")
    return Column(name=name, relation=rel, range=rng, match=match)


def _table(spec: model.OntologySpec, name: str, raw: dict) -> Table:
    if not _NAME.match(name):
        raise ValueError(f"table {name!r} must be a plain name")
    logical = str(raw.get("logical_table") or name)
    if not _NAME.match(logical):
        raise ValueError(f"table {name!r} logical_table {logical!r} must be a plain name")
    location = str(raw.get("location") or "").strip()
    if not location or ".." in location.split("/") or location.startswith("/"):
        raise ValueError(f"table {name!r} location must be a relative path or coa:<dataSourceId>")
    cls = str(raw.get("class") or "")
    if cls not in spec.classes:
        raise ValueError(f"table {name!r} class {cls!r} is not in the ontology")
    key = raw.get("key") or []
    if isinstance(key, str):
        key = [key]
    if not key or any(not _NAME.match(str(k)) for k in key):
        raise ValueError(f"table {name!r} needs a key of column names")
    cols_raw = raw.get("columns") or {}
    if not isinstance(cols_raw, dict) or not cols_raw:
        raise ValueError(f"table {name!r} needs columns")
    columns = tuple(_column(spec, cls, str(n), c) for n, c in cols_raw.items())
    # The key is a field in the file. It identifies the row and does not have to be an attribute.
    scope = str(raw.get("scope") or "public")
    if scope not in ("public", "private"):
        raise ValueError(f"table {name!r} scope must be public or private")
    return Table(name=name, location=location, logical_table=logical, class_name=cls,
                 key=tuple(str(k) for k in key), columns=columns, scope=scope)


def _metrics(spec: model.OntologySpec, tables: tuple[Table, ...], raw) -> tuple[Metric, ...]:
    logical = {t.logical_table for t in tables}
    out = []
    for m in (raw or {}).get("metrics") or []:
        name = str(m.get("name") or "")
        if not _NAME.match(name):
            raise ValueError(f"metric name {name!r} must be a plain name")
        dialects = ((m.get("expression") or {}).get("dialects") or [])
        ansi = next((d.get("expression") for d in dialects if str(d.get("dialect") or "").upper() == "ANSI_SQL"), "")
        expr = _check_select(str(ansi or ""), name)
        coa = next((x.get("data") or {} for x in m.get("custom_extensions") or []
                    if (x.get("vendor_name") or "") == "COA"), {})
        source = str(coa.get("source_table") or "")
        if source not in logical:
            raise ValueError(f"metric {name!r} source_table {source!r} is not a logical_table in the mapping")
        concepts = tuple(str(c) for c in coa.get("ontology_concepts") or [])
        missing = [c for c in concepts if c not in spec.classes]
        if missing:
            raise ValueError(f"metric {name!r} ontology concept {missing[0]!r} is not a class")
        out.append(Metric(name=name, description=str(m.get("description") or ""), expression=expr,
                          source_table=source, concepts=concepts, unit=str(coa.get("unit") or ""),
                          return_type=str(coa.get("return_type") or "")))
    names = [m.name for m in out]
    if len(names) != len(set(names)):
        raise ValueError("a metric name is used twice")
    return tuple(out)


def _joins(tables: tuple[Table, ...]) -> None:
    by_class = {t.class_name: t for t in tables}
    for t in tables:
        for c in t.columns:
            if not c.relation:
                continue
            other = by_class.get(c.range)
            if other is None:
                raise ValueError(f"column {c.name!r} joins to {c.range}, which has no table in this mapping")
            if other.column(c.match) is None and c.match not in other.key:
                raise ValueError(f"column {c.name!r} match {c.match!r} is not a column or key of {c.range}")


def load(src: str | Path, spec: model.OntologySpec) -> Mapping | None:
    """The mapping in src, checked against spec. None when the directory has neither file.
    ValueError names the first thing that does not match the ontology."""
    import yaml
    src = Path(src)
    mapping_path, metric_path = src / "mappings.yaml", src / "metrics.osi.yaml"
    if not mapping_path.exists() and not metric_path.exists():
        return None
    if not mapping_path.exists():
        raise ValueError("metrics.osi.yaml needs mappings.yaml beside it")
    raw = yaml.safe_load(mapping_path.read_text()) or {}
    tables_raw = raw.get("tables") or {}
    if not isinstance(tables_raw, dict) or not tables_raw:
        raise ValueError("mappings.yaml needs a tables mapping")
    tables = tuple(_table(spec, str(n), t) for n, t in tables_raw.items())
    logical = [t.logical_table for t in tables]
    if len(logical) != len(set(logical)):
        raise ValueError("two tables share a logical_table")
    classes = [t.class_name for t in tables]
    if len(classes) != len(set(classes)):
        raise ValueError("two tables fill the same class")
    _joins(tables)
    metrics = ()
    if metric_path.exists():
        metrics = _metrics(spec, tables, yaml.safe_load(metric_path.read_text()) or {})
    return Mapping(tables, metrics)


def change_kind(old: Mapping | None, new: Mapping | None) -> tuple[str, list[str]]:
    """How the mapping changed: none, descriptive, additive, semantic or removal.

    A label or a metric's wording is descriptive. A new column, metric or table is
    additive. A key, a class, a datatype or a relation's range is semantic. Removing
    a table, column or metric is removal.
    """
    if old is None and new is None:
        return "none", []
    if old is None:
        return "additive", [f"table {t.logical_table}" for t in new.tables] + [f"metric {m.name}" for m in new.metrics]
    if new is None:
        return "removal", [f"table {t.logical_table} removed" for t in old.tables]
    notes: list[str] = []
    kind = "none"
    rank = {"none": 0, "descriptive": 1, "additive": 2, "semantic": 3, "removal": 4}

    def bump(k: str, note: str) -> None:
        nonlocal kind
        notes.append(note)
        if rank[k] > rank[kind]:
            kind = k

    old_t = {t.logical_table: t for t in old.tables}
    new_t = {t.logical_table: t for t in new.tables}
    for name in sorted(set(old_t) - set(new_t)):
        bump("removal", f"table {name} removed")
    for name in sorted(set(new_t) - set(old_t)):
        bump("additive", f"table {name}")
    for name in sorted(set(old_t) & set(new_t)):
        a, b = old_t[name], new_t[name]
        if (a.class_name, a.key, a.location, a.scope) != (b.class_name, b.key, b.location, b.scope):
            bump("semantic", f"table {name}: key, class, location or scope")
        ac = {c.name: c for c in a.columns}
        bc = {c.name: c for c in b.columns}
        for col in sorted(set(ac) - set(bc)):
            bump("removal", f"table {name} column {col} removed")
        for col in sorted(set(bc) - set(ac)):
            bump("additive", f"table {name} column {col}")
        for col in sorted(set(ac) & set(bc)):
            x, y = ac[col], bc[col]
            if (x.attribute, x.relation, x.range, x.match, x.datatype) != (y.attribute, y.relation, y.range, y.match, y.datatype):
                bump("semantic", f"table {name} column {col}: datatype, relation or range")
    old_m = {m.name: m for m in old.metrics}
    new_m = {m.name: m for m in new.metrics}
    for name in sorted(set(old_m) - set(new_m)):
        bump("removal", f"metric {name} removed")
    for name in sorted(set(new_m) - set(old_m)):
        bump("additive", f"metric {name}")
    for name in sorted(set(old_m) & set(new_m)):
        a, b = old_m[name], new_m[name]
        if (a.expression, a.source_table, a.concepts, a.return_type) != (b.expression, b.source_table, b.concepts, b.return_type):
            bump("semantic", f"metric {name}: expression, table or concepts")
        elif a.description != b.description or a.unit != b.unit:
            bump("descriptive", f"metric {name}: wording")
    return kind, notes


def subject_template(spec: model.OntologySpec, table: Table) -> str:
    """The row IRI template: the class and the key columns, not a normalised label."""
    base = spec.namespace.rstrip("#/")
    keys = "/".join("{" + k + "}" for k in table.key)
    return f"{base}/{table.class_name}/{keys}"


def _parent_column(tables: tuple[Table, ...], col: Column) -> str:
    other = next(t for t in tables if t.class_name == col.range)
    match = other.column(col.match)
    return match.name if match else col.match


def r2rml(spec: model.OntologySpec, mapping: Mapping) -> str:
    """The triples maps a virtual knowledge graph reads. Generated, never edited."""
    prefix = spec.namespace if spec.namespace.endswith("#") or spec.namespace.endswith("/") else spec.namespace + "#"
    lines = [
        "# Generated from mappings.yaml. Do not edit: publish writes this again.",
        "@prefix rr:  <http://www.w3.org/ns/r2rml#> .",
        f"@prefix o:   <{prefix}> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
        "",
    ]
    xsd = {"integer": "xsd:integer", "decimal": "xsd:decimal", "date": "xsd:date", "boolean": "xsd:boolean"}
    for table in mapping.tables:
        lines.append(f"<#{table.class_name}Map>")
        lines.append(f'    rr:logicalTable [ rr:tableName "{table.logical_table}" ] ;')
        lines.append("    rr:subjectMap [")
        lines.append(f'        rr:template "{subject_template(spec, table)}" ;')
        lines.append(f"        rr:class o:{table.class_name}")
        lines.append("    ] ;")
        chunks = []
        for col in table.columns:
            if col.attribute:
                dt = f" ; rr:datatype {xsd[col.datatype]}" if col.datatype in xsd else ""
                chunks.append(f"    rr:predicateObjectMap [\n        rr:predicate o:{col.attribute} ;\n"
                              f'        rr:objectMap [ rr:column "{col.name}"{dt} ]\n    ]')
            else:
                parent = _parent_column(mapping.tables, col)
                chunks.append(
                    f"    rr:predicateObjectMap [\n        rr:predicate o:{col.relation} ;\n"
                    f"        rr:objectMap [\n            rr:parentTriplesMap <#{col.range}Map> ;\n"
                    f'            rr:joinCondition [ rr:child "{col.name}" ; rr:parent "{parent}" ]\n'
                    f"        ]\n    ]")
        lines.append(" ;\n".join(chunks) + " .\n")
    return "\n".join(lines)


def agent_lines(mapping: Mapping | None) -> list[str]:
    """One line per mapped type, for the agent rendition. The snapshot is what the tools report."""
    if not mapping or not mapping.tables:
        return []
    lines = ["", "## Mapped tables",
             "A filter or a total over one of these uses describe_structured, then lookup_rows or aggregate. "
             "Cite the cell the tool returns. These are not passage quotes."]
    for t in mapping.tables:
        cols = ", ".join(c.attribute or c.relation for c in t.columns)
        lines.append(f"- {t.class_name} from `{t.logical_table}` ({t.location}), key {', '.join(t.key)}: {cols}")
    for m in mapping.metrics:
        lines.append(f"- metric {m.name} over `{m.source_table}`: {m.description}")
    return lines
