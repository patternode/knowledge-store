"""Bind: copy each mapped CSV into gold at the hash of its bytes.

Runs after extract, for the active version. Refine has already skipped these files, so
they never become passages. A row's IRI is the class plus the key, which is why a table
"NASA" and a document "National Aeronautics and Space Administration" stay two nodes.

A relation column matches the object by `match` inside this same bind. A miss is recorded
in the report and the triple is not invented. The previous snapshot stays where it was:
a citation names the snapshot it was checked against.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import json
from urllib.parse import quote

from .. import layout
from ..store import Store, put_json
from .mapping import Mapping, Table, subject_template

# The same full kinds as ontology.versions.FULL_KINDS. Repeated here so a tool Lambda can walk
# the chain from manifest JSON without importing the ontology parser.
_FULL_KINDS = ("initial", "semantic", "removal")


def active(lake: Store) -> str | None:
    """The active ontology version, from the pointer alone."""
    if not lake.exists(layout.ONTOLOGY_ACTIVE):
        return None
    return json.loads(lake.get(layout.ONTOLOGY_ACTIVE)).get("version")


def chain(lake: Store, version: str) -> list[str]:
    """The versions whose gold makes up version's graph, newest first."""
    out, v = [], version
    while v:
        out.append(v)
        key = f"{layout.ontology_version_prefix(v)}/manifest.json"
        if not lake.exists(key):
            break
        manifest = json.loads(lake.get(key))
        if manifest.get("kind") in _FULL_KINDS:
            break
        v = manifest.get("base")
    return out


def published_mapping(lake: Store, version: str | None = None) -> Mapping | None:
    version = version or active(lake)
    if not version:
        return None
    key = f"{layout.ontology_version_prefix(version)}/renditions/structured/mapping.json"
    if not lake.exists(key):
        return None
    return Mapping.from_json(json.loads(lake.get(key)))


def matches(meta: dict, location: str) -> bool:
    """Whether a bronze object is the file the mapping names."""
    key = str(meta.get("source_key") or "").replace("\\", "/")
    if key == location or key.endswith("/" + location):
        return True
    folder = str((meta.get("metadata") or {}).get("folder") or "").strip("/")
    name = str(meta.get("name") or "")
    rel = f"{folder}/{name}" if folder else name
    return rel == location


def mapped_doc_ids(lake: Store) -> set[str]:
    """Bronze objects a published mapping names, so refine and extract leave them alone."""
    mapping = published_mapping(lake)
    if mapping is None:
        return set()
    from ..pipeline.ingest import bronze_objects
    paths = mapping.locations()
    return {doc_id for doc_id, meta in bronze_objects(lake).items() if any(matches(meta, p) for p in paths)}


def _read_rows(data: bytes, location: str) -> list[dict]:
    text = data.decode("utf-8-sig")
    if location.endswith(".json"):
        raw = json.loads(text)
        if not isinstance(raw, list) or any(not isinstance(r, dict) for r in raw):
            raise ValueError(f"{location} is not a JSON array of objects")
        return [{str(k): "" if v is None else str(v) for k, v in row.items()} for row in raw]
    dialect = csv.excel_tab if location.endswith(".tsv") else csv.excel
    return [{k: (v or "").strip() for k, v in row.items() if k} for row in csv.DictReader(io.StringIO(text), dialect=dialect)]


def _iri(spec, table: Table, key: str) -> str:
    template = subject_template(spec, table)
    # One key column is the common case. Several keys fill the template left to right.
    parts = key.split(",")
    out = template
    for col, part in zip(table.key, parts):
        out = out.replace("{" + col + "}", quote(part, safe="-_."))
    return out


def _scope(table: Table, meta: dict) -> str:
    return "private" if table.scope == "private" or meta.get("scope") == "private" else "public"


def _find(objects: dict, location: str) -> tuple[str, dict] | None:
    hits = [(i, m) for i, m in objects.items() if matches(m, location)]
    if not hits:
        return None
    exact = [h for h in hits if str(h[1].get("source_key") or "").endswith(location)]
    return (exact or hits)[0]


def binding(lake: Store, version: str | None = None) -> dict:
    """The snapshot each table is bound to, walking back the version chain."""
    version = version or active(lake)
    if not version:
        return {}
    found: dict = {}
    for v in chain(lake, version):
        key = layout.structured_binding_key(v)
        if not lake.exists(key):
            continue
        for name, row in json.loads(lake.get(key)).items():
            found.setdefault(name, row)
    return found


def bind(lake: Store, version: str | None = None) -> dict:
    """Copy mapped tables into gold/<version>/structured. Unchanged snapshots are left as they are."""
    from rdflib import RDF, RDFS, Graph, Literal, URIRef

    from ..extract.rdf import Iris
    from ..extract.validate import parse_value
    from ..ontology import versions
    from ..ontology.model import DATATYPES, KL
    version = version or active(lake)
    mapping = published_mapping(lake, version) if version else None
    if not version or mapping is None:
        return {"written": 0, "unchanged": 0, "missing": [], "misses": []}
    spec, shapes = versions.load_version(lake, version)
    from ..pipeline.ingest import bronze_objects
    objects = bronze_objects(lake)
    prior = binding(lake, version)
    out_binding = dict(prior)
    written = unchanged = 0
    missing, misses = [], []
    parsed: dict[str, tuple] = {}
    for table in mapping.tables:
        if table.location.startswith("coa:"):
            missing.append({"table": table.logical_table, "reason": "live source, not copied"})
            continue
        found = _find(objects, table.location)
        if found is None:
            missing.append({"table": table.logical_table, "location": table.location})
            continue
        doc_id, meta = found
        source = meta.get("source") or "uploads"
        held = prior.get(table.logical_table) or {}
        if held.get("snapshot") == doc_id and lake.exists(held.get("cells", "")):
            out_binding[table.logical_table] = held
            unchanged += 1
            data = lake.get(meta["content_key"])
            parsed[table.logical_table] = (table, meta, doc_id, _read_rows(data, table.location), source)
            continue
        data = lake.get(meta["content_key"])
        parsed[table.logical_table] = (table, meta, doc_id, _read_rows(data, table.location), source)

    # Index every row of this bind by the values a relation may match, including rows whose
    # snapshot did not change: a new table can join to an old one.
    indexes: dict[str, dict[str, dict[str, str]]] = {}
    for logical, (table, meta, doc_id, rows, source) in parsed.items():
        idx: dict[str, dict[str, str]] = {}
        for row in rows:
            key = ",".join((row.get(k) or "").strip() for k in table.key)
            if not key or any(not (row.get(k) or "").strip() for k in table.key):
                misses.append({"table": logical, "reason": "row has no key"})
                continue
            iri = _iri(spec, table, key)
            fields = [(name, (row.get(name) or "").strip()) for name in table.key]
            fields += [(col.attribute or col.name, (row.get(col.name) or "").strip()) for col in table.columns]
            for field, value in fields:
                if not value:
                    continue
                slot = idx.setdefault(field, {})
                if value in slot and slot[value] != iri:
                    slot[value] = ""  # ambiguous: a join will miss rather than guess
                else:
                    slot.setdefault(value, iri)
        indexes[logical] = idx

    run_id = "bind-" + dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%S")
    ids = Iris(spec)
    for logical, (table, meta, doc_id, rows, source) in parsed.items():
        held = prior.get(logical) or {}
        if held.get("snapshot") == doc_id and lake.exists(held.get("cells", "")):
            continue
        scope = _scope(table, meta)
        g = Graph()
        g.bind("ks", KL)
        g.bind("o", spec.namespace)
        cells = []
        run = ids.run(run_id + "-" + logical)
        g.add((run, RDF.type, KL.ExtractionRun))
        g.add((run, KL.modelId, Literal("bind")))
        g.add((run, KL.ontologyVersion, Literal(version)))
        seen_keys = set()
        for row in rows:
            key = ",".join((row.get(k) or "").strip() for k in table.key)
            if not key or key in seen_keys or any(not (row.get(k) or "").strip() for k in table.key):
                continue
            seen_keys.add(key)
            node = URIRef(_iri(spec, table, key))
            g.add((node, RDF.type, spec.iri_of(table.class_name)))
            g.add((node, KL.scope, Literal(scope)))
            label = next(((row.get(c.name) or "").strip() for c in table.columns if c.attribute == "name"), "") or key
            g.add((node, RDFS.label, Literal(label)))
            for col in table.columns:
                value = (row.get(col.name) or "").strip()
                if not value:
                    continue
                cell_id = f"c:{source}/{doc_id}/{logical}/{quote(key, safe='-_.,')}/{col.name}"
                cell = ids._iri("cell", cell_id)
                g.add((cell, RDF.type, KL.Cell))
                g.add((cell, KL.column, Literal(col.name)))
                g.add((cell, KL.cellValue, Literal(value)))
                g.add((cell, KL.snapshot, Literal(doc_id)))
                g.add((cell, KL.rowKey, Literal(key)))
                g.add((cell, KL.source, Literal(source)))
                g.add((cell, KL.scope, Literal(scope)))
                cells.append({"cell": cell_id, "source": source, "snapshot": doc_id, "table": logical,
                              "key": key, "column": col.name, "value": value, "datatype": col.datatype or "string",
                              "scope": scope, "class": table.class_name,
                              "attribute": col.attribute, "relation": col.relation})
                if col.attribute:
                    try:
                        py = parse_value(value, col.datatype or "string")
                    except ValueError as e:
                        misses.append({"table": logical, "key": key, "column": col.name, "reason": str(e)})
                        continue
                    lit = Literal(py, datatype=DATATYPES[col.datatype]) if col.datatype and col.datatype != "string" else Literal(str(py))
                    pred = URIRef(spec.attributes[col.attribute].iri)
                    _assert(g, ids, node, pred, lit, run, cell)
                else:
                    parent = indexes.get(next((t.logical_table for t in mapping.tables if t.class_name == col.range), ""), {})
                    target = (parent.get(col.match) or parent.get(col.name) or {}).get(value, "")
                    if not target:
                        misses.append({"table": logical, "key": key, "column": col.name,
                                       "reason": f"no {col.range} with {col.match} {value!r}"})
                        continue
                    _assert(g, ids, node, URIRef(spec.relations[col.relation].iri), URIRef(target), run, cell)
        graph_key = layout.structured_graph_key(version, source, doc_id)
        cells_key = layout.structured_cells_key(version, source, doc_id)
        from ..extract.validate import shacl_errors
        from ..ontology.model import CORE_SHAPES, CORE_TTL
        shape_g = Graph().parse(str(CORE_SHAPES), format="turtle")
        if shapes is not None:
            for triple in shapes:
                shape_g.add(triple)
        tbox = Graph().parse(str(CORE_TTL), format="turtle")
        if spec.graph is not None:
            for triple in spec.graph:
                tbox.add(triple)
        conforms, msgs, _ = shacl_errors(g, shape_g, tbox)
        if not conforms:
            misses.append({"table": logical, "reason": "snapshot failed SHACL", "messages": msgs[:8]})
            continue
        quads = _nquads(g, ids.graph(version, f"structured-{source}-{doc_id}"))
        lake.put(graph_key, quads, "application/n-quads")
        lake.put(cells_key, ("\n".join(json.dumps(c) for c in cells) + ("\n" if cells else "")).encode(),
                 "application/x-ndjson")
        out_binding[logical] = {"source": source, "snapshot": doc_id, "location": table.location, "scope": scope,
                                "rows": len(seen_keys), "class": table.class_name, "graph": graph_key, "cells": cells_key}
        written += 1
    # Drop tables the mapping no longer names, without deleting the old snapshot files: a citation
    # of an earlier snapshot still resolves.
    for name in list(out_binding):
        if mapping.table(name) is None and name not in {t.logical_table for t in mapping.tables}:
            out_binding.pop(name, None)
    put_json(lake, layout.structured_binding_key(version), out_binding)
    return {"written": written, "unchanged": unchanged, "missing": missing, "misses": misses,
            "tables": sorted(out_binding)}


def _assert(g, ids, s, p, o, run, cell) -> None:
    from rdflib import RDF

    from ..ontology.model import KL
    a = ids.assertion(s, p, o)
    g.add((s, p, o))
    g.add((a, RDF.type, KL.Assertion))
    g.add((a, RDF.subject, s))
    g.add((a, RDF.predicate, p))
    g.add((a, RDF.object, o))
    g.add((a, KL.extractedBy, run))
    g.add((a, KL.recordedIn, cell))


def _nquads(g, graph) -> bytes:
    from rdflib import Dataset
    ds = Dataset()
    ctx = ds.graph(graph)
    for triple in g:
        ctx.add(triple)
    return ds.serialize(format="nquads").encode()
