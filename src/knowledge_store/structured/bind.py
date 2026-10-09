"""Bind: copy each mapped CSV into gold at the hash of its bytes.

Runs after extract, for the active version. Refine has already skipped these files, so
they never become passages. A row's IRI is the class plus the key, which is why a table
"NASA" and a document "National Aeronautics and Space Administration" stay two nodes.

A relation column matches the object by `match` inside this same bind. A miss is recorded
in the report and the triple is not invented. The previous snapshot stays where it was:
a citation names the snapshot it was checked against.

A table is rebound when its file, its mapping (the hash of the table's mapping JSON) or its
scope changes; only when all three are the same is the held snapshot kept. A number or a date
is stored in its canonical form (values.canonical: 1100, 2023-07-14) with the text the file held
as `raw`, so filters, totals and citation checks read one form. Every key column gets a cell
too, so a filter can name the key and a count sees every row.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
from urllib.parse import quote, unquote

from .. import layout
from ..store import Store, put_json
from .mapping import Mapping, Table, subject_template

MAX_TABLE_BYTES = 50 * 1024 * 1024   # a mapped file larger than this is not bound
MAX_TABLE_ROWS = 200_000

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


def _paths(meta: dict) -> list[str]:
    """Every path this bronze object was uploaded under, plus folder/name from the adapter."""
    raw = [meta.get("source_key"), *(meta.get("source_keys") or [])]
    out = []
    for item in raw:
        key = str(item or "").replace("\\", "/")
        if key and key not in out:
            out.append(key)
    folder = str((meta.get("metadata") or {}).get("folder") or "").replace("\\", "/").strip("/")
    name = str(meta.get("name") or "")
    rel = f"{folder}/{name}" if folder and name else name
    if rel and rel not in out:
        out.append(rel)
    return out


def _rank(meta: dict, location: str) -> int:
    """How closely a bronze object is the file the mapping names.

    0 the path is the location, 1 the path ends with it, 2 only the file name matches
    (a catalog uploaded beside the documents, or copied out of tables/). -1 is not a match.
    """
    location = location.replace("\\", "/").lstrip("/")
    if not location:
        return -1
    base = location.rsplit("/", 1)[-1]
    best = 99
    for key in _paths(meta):
        if key == location:
            best = min(best, 0)
        elif key.endswith("/" + location):
            best = min(best, 1)
        elif base and key.rsplit("/", 1)[-1] == base:
            best = min(best, 2)
    return -1 if best == 99 else best


def matches(meta: dict, location: str) -> bool:
    """Whether a bronze object is the file the mapping names."""
    return _rank(meta, location) >= 0


def _select(objects: dict, location: str) -> tuple[tuple[str, dict] | None, str]:
    """The bronze object for a location. Two equally good files are not a guess."""
    hits = [(_rank(meta, location), doc_id, meta) for doc_id, meta in objects.items()]
    hits = [h for h in hits if h[0] >= 0]
    if not hits:
        return None, ""
    best = min(h[0] for h in hits)
    chosen = [h for h in hits if h[0] == best]
    if len(chosen) > 1:
        base = location.replace("\\", "/").rsplit("/", 1)[-1]
        return None, f"more than one file named {base}"
    return (chosen[0][1], chosen[0][2]), ""


def mapped_doc_ids(lake: Store) -> set[str]:
    """Bronze objects a published mapping names, so refine and extract leave them alone.

    An ambiguous name is left as a document: bind will say which file it could not choose.
    """
    mapping = published_mapping(lake)
    if mapping is None:
        return set()
    from ..pipeline.ingest import bronze_objects
    objects = bronze_objects(lake)
    chosen = set()
    for path in mapping.locations():
        found, _why = _select(objects, path)
        if found:
            chosen.add(found[0])
    return chosen


def _read_rows(data: bytes, location: str) -> list[dict]:
    """The rows of a mapped file, or a ValueError saying why it cannot be bound."""
    if len(data) > MAX_TABLE_BYTES:
        raise ValueError(f"{location} is larger than {MAX_TABLE_BYTES // (1024 * 1024)} MB")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError(f"{location} is not UTF-8 text") from None
    if location.endswith(".json"):
        try:
            raw = json.loads(text)
        except ValueError:
            raise ValueError(f"{location} is not valid JSON") from None
        if not isinstance(raw, list) or any(not isinstance(r, dict) for r in raw):
            raise ValueError(f"{location} is not a JSON array of objects")
        rows = [{str(k).strip(): "" if v is None else str(v).strip() for k, v in row.items()} for row in raw]
    else:
        reader = csv.reader(io.StringIO(text), dialect=csv.excel_tab if location.endswith(".tsv") else csv.excel)
        header = [h.strip() for h in next(reader, [])]
        dupes = sorted({h for h in header if h and header.count(h) > 1})
        if dupes:
            raise ValueError(f"{location} has more than one column named {', '.join(dupes)}")
        rows = [{h: (v or "").strip() for h, v in zip(header, rec) if h} for rec in reader if any(x.strip() for x in rec)]
    if len(rows) > MAX_TABLE_ROWS:
        raise ValueError(f"{location} has more than {MAX_TABLE_ROWS} rows")
    return rows


def key_text(parts) -> str:
    """A row's key as text: the value itself for one key column; for several, each part with its
    commas and percent signs escaped, joined by commas, so no two rows share a key."""
    parts = [str(p) for p in parts]
    if len(parts) == 1:
        return parts[0]
    return ",".join(p.replace("%", "%25").replace(",", "%2C") for p in parts)


def key_parts(table: Table, text: str) -> list[str]:
    return [text] if len(table.key) == 1 else [unquote(p) for p in text.split(",")]


def _row_key(table: Table, row: dict) -> tuple[str, ...] | None:
    parts = tuple((row.get(k) or "").strip() for k in table.key)
    return parts if parts and all(parts) else None


def _iri(spec, table: Table, parts) -> str:
    out = subject_template(spec, table)
    # One key column is the common case. Several keys fill the template left to right.
    for col, part in zip(table.key, parts):
        out = out.replace("{" + col + "}", quote(part, safe="-_."))
    return out


def mapping_hash(table: Table) -> str:
    """What the binding remembers of the table's mapping: a change rebinds the table."""
    return hashlib.sha256(json.dumps(table.to_json(), sort_keys=True).encode()).hexdigest()[:16]


def _scope(table: Table, meta: dict) -> str:
    return "private" if table.scope == "private" or meta.get("scope") == "private" else "public"


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
    from ..values import canonical, parse_value
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
        found, why = _select(objects, table.location)
        if found is None:
            row = {"table": table.logical_table, "location": table.location}
            if why:
                row["reason"] = why
            missing.append(row)
            continue
        doc_id, meta = found
        source = meta.get("source") or "uploads"
        try:
            rows = _read_rows(lake.get(meta["content_key"]), table.location)
        except ValueError as e:
            missing.append({"table": table.logical_table, "location": table.location, "reason": str(e)})
            continue
        if _unchanged(lake, prior.get(table.logical_table) or {}, table, meta, doc_id):
            out_binding[table.logical_table] = prior[table.logical_table]
            unchanged += 1
        parsed[table.logical_table] = (table, meta, doc_id, rows, source)

    # Index every row of this bind by the values a relation may match, including rows whose
    # snapshot did not change: a new table can join to an old one.
    indexes: dict[str, dict[str, dict[str, str]]] = {}
    for logical, (table, meta, doc_id, rows, source) in parsed.items():
        idx: dict[str, dict[str, str]] = {}
        for row in rows:
            parts = _row_key(table, row)
            if parts is None:
                misses.append({"table": logical, "reason": "row has no key"})
                continue
            iri = _iri(spec, table, parts)
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
        if _unchanged(lake, prior.get(logical) or {}, table, meta, doc_id):
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
            parts = _row_key(table, row)
            key = key_text(parts) if parts else ""
            if not key or key in seen_keys:
                continue
            seen_keys.add(key)
            node = URIRef(_iri(spec, table, parts))
            g.add((node, RDF.type, spec.iri_of(table.class_name)))
            g.add((node, KL.scope, Literal(scope)))
            label = next(((row.get(c.name) or "").strip() for c in table.columns if c.attribute == "name"), "") or key
            g.add((node, RDFS.label, Literal(label)))
            mapped = {c.name for c in table.columns}

            def add_cell(name: str, value: str, raw: str, datatype: str, attribute: str = "", relation: str = "",
                         invalid: bool = False):
                cell_id = f"c:{source}/{doc_id}/{logical}/{quote(key, safe='-_.,')}/{name}"
                cell = ids._iri("cell", cell_id)
                g.add((cell, RDF.type, KL.Cell))
                g.add((cell, KL.column, Literal(name)))
                g.add((cell, KL.cellValue, Literal(value)))
                g.add((cell, KL.snapshot, Literal(doc_id)))
                g.add((cell, KL.rowKey, Literal(key)))
                g.add((cell, KL.source, Literal(source)))
                g.add((cell, KL.scope, Literal(scope)))
                rec = {"cell": cell_id, "source": source, "snapshot": doc_id, "table": logical, "key": key,
                       "column": name, "value": value, "datatype": datatype, "scope": scope,
                       "class": table.class_name, "attribute": attribute, "relation": relation}
                if raw != value:
                    rec["raw"] = raw
                if invalid:
                    rec["invalid"] = True
                cells.append(rec)
                return cell

            # Key columns that are not mapped columns still get a cell: a filter may name the key,
            # and a count must see a row whose other columns are all empty.
            for k, part in zip(table.key, parts):
                if k not in mapped:
                    add_cell(k, part, part, "string")
            for col in table.columns:
                raw = (row.get(col.name) or "").strip()
                if not raw:
                    continue
                datatype = col.datatype or "string"
                if col.attribute:
                    try:
                        py = parse_value(raw, datatype)
                    except ValueError as e:
                        add_cell(col.name, raw, raw, datatype, col.attribute, col.relation, invalid=True)
                        misses.append({"table": logical, "key": key, "column": col.name, "reason": str(e)})
                        continue
                    cell = add_cell(col.name, canonical(raw, datatype), raw, datatype, col.attribute, col.relation)
                    lit = Literal(py, datatype=DATATYPES[col.datatype]) if col.datatype and col.datatype != "string" else Literal(str(py))
                    pred = URIRef(spec.attributes[col.attribute].iri)
                    _assert(g, ids, node, pred, lit, run, cell)
                else:
                    value = raw
                    cell = add_cell(col.name, raw, raw, datatype, col.attribute, col.relation)
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
                                "rows": len(seen_keys), "class": table.class_name, "graph": graph_key, "cells": cells_key,
                                "mapping": mapping_hash(table)}
        written += 1
    # Drop tables the mapping no longer names, without deleting the old snapshot files: a citation
    # of an earlier snapshot still resolves.
    for name in list(out_binding):
        if mapping.table(name) is None and name not in {t.logical_table for t in mapping.tables}:
            out_binding.pop(name, None)
    put_json(lake, layout.structured_binding_key(version), out_binding)
    return {"written": written, "unchanged": unchanged, "missing": missing, "misses": misses,
            "tables": sorted(out_binding)}


def _unchanged(lake: Store, held: dict, table: Table, meta: dict, doc_id: str) -> bool:
    """Whether the held snapshot still stands: the same file, the same mapping and the same scope."""
    return (held.get("snapshot") == doc_id and held.get("mapping") == mapping_hash(table)
            and held.get("scope") == _scope(table, meta) and lake.exists(held.get("cells", "")))


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
