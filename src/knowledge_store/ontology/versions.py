"""Ontology versions: publish, activate, diff and classify.

A version is authored in git (the master: a directory holding ontology.ttl and optionally
shapes.ttl) and published into the lake, where it is immutable: publishing a version that exists
is refused. The lake copy is what extraction reads; git is where people edit and review. Each
release also renders the master into its derived forms (renditions.py: OWL and SHACL, an
agent vocabulary, a Neo4j schema and mapping, the extraction tool schema, a JSON-LD context).

Every publish is diffed against the version it follows, and the change is classified with the
taxonomy:

    descriptive  labels, synonyms, definitions, or the     patch   no re-extraction
                 ontology's own label or comment
    additive     new classes or properties, nothing else   minor   delta extraction of the new terms
    semantic     parents, domains or ranges changed        major   full re-extraction
    removal      a term removed or deprecated              major   full re-extraction

A new subclass of an existing class counts as additive: entity IRIs are keyed by root class
(extract/rdf.py), so a delta run can retype an existing entity without duplicating it. The
semver bump must match the class, so a version number tells a reader what it costs.

Versions form a chain. An additive or descriptive version names its base, and its gold holds
only the delta; the projection for a version is the union of gold along the chain back to the
last full (initial, semantic or removal) version. That is what makes ontologies cumulative.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from .. import layout
from ..store import Store, put_json
from . import model

SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
FULL_KINDS = ("initial", "semantic", "removal")


@dataclass
class Diff:
    added: list[str]
    removed: list[str]
    semantic: list[str]
    descriptive: list[str]

    @property
    def kind(self) -> str:
        if self.removed:
            return "removal"
        if self.semantic:
            return "semantic"
        if self.added:
            return "additive"
        if self.descriptive:
            return "descriptive"
        return "none"

    def to_dict(self) -> dict:
        return {"kind": self.kind, "added": self.added, "removed": self.removed,
                "semantic": self.semantic, "descriptive": self.descriptive}


def diff(old: model.OntologySpec, new: model.OntologySpec) -> Diff:
    def terms(s: model.OntologySpec) -> dict[str, model.Term]:
        return {**s.classes, **s.relations, **s.attributes}

    a, b = terms(old), terms(new)
    added = sorted(set(b) - set(a))
    removed = sorted(set(a) - set(b))
    semantic, descriptive = [], []
    for k in sorted(set(a) & set(b)):
        x, y = a[k], b[k]
        if type(x) is not type(y):
            semantic.append(f"{k}: changed from {type(x).__name__} to {type(y).__name__}")
            continue
        if isinstance(x, model.ClassTerm) and set(x.parents) != set(y.parents):
            semantic.append(f"{k}: parents {sorted(x.parents)} -> {sorted(y.parents)}")
        if isinstance(x, model.PropertyTerm) and (set(x.domain) != set(y.domain) or set(x.range) != set(y.range)):
            semantic.append(f"{k}: signature {list(x.domain)}->{list(x.range)} to {list(y.domain)}->{list(y.range)}")
        if (x.label, set(x.alt_labels), x.definition) != (y.label, set(y.alt_labels), y.definition):
            descriptive.append(k)
    # The ontology's own label and comment describe it, as a term's do; its version IRI changes
    # with every version, so it is checked against the version instead (publish).
    if (old.label, old.comment) != (new.label, new.comment):
        descriptive.append("(ontology header)")
    return Diff(added, removed, semantic, descriptive)


def required_bump(kind: str) -> str:
    return {"descriptive": "patch", "additive": "minor", "semantic": "major", "removal": "major"}.get(kind, "none")


def bump_of(old: str, new: str) -> str:
    o, n = SEMVER.match(old), SEMVER.match(new)
    if not o or not n:
        raise ValueError(f"versions must be semver X.Y.Z: {old!r} -> {new!r}")
    o, n = tuple(map(int, o.groups())), tuple(map(int, n.groups()))
    if n <= o:
        raise ValueError(f"version {new} does not follow {old}")
    if n[0] > o[0]:
        return "major"
    if n[1] > o[1]:
        return "minor"
    return "patch"


def active_version(lake: Store) -> str | None:
    if not lake.exists(layout.ONTOLOGY_ACTIVE):
        return None
    return json.loads(lake.get(layout.ONTOLOGY_ACTIVE)).get("version")


def manifest(lake: Store, version: str) -> dict:
    return json.loads(lake.get(f"{layout.ontology_version_prefix(version)}/manifest.json"))


def load_version(lake: Store, version: str) -> tuple[model.OntologySpec, "object | None"]:
    """The spec and the version's own SHACL shapes graph (or None)."""
    from rdflib import Graph
    pre = layout.ontology_version_prefix(version)
    spec = model.load(data=lake.get(f"{pre}/ontology.ttl").decode())
    shapes = None
    if lake.exists(f"{pre}/shapes.ttl"):
        shapes = Graph().parse(data=lake.get(f"{pre}/shapes.ttl").decode(), format="turtle")
    return spec, shapes


def chain(lake: Store, version: str) -> list[str]:
    """The versions whose gold makes up version's graph, newest first."""
    out, v = [], version
    while v:
        out.append(v)
        m = manifest(lake, v)
        if m["kind"] in FULL_KINDS:
            break
        v = m.get("base")
    return out


def published_versions(lake: Store) -> list[str]:
    vs = {k.split("/")[2] for k in lake.list(layout.ONTOLOGY_VERSIONS + "/") if k.endswith("/manifest.json")}
    return sorted(vs, key=lambda v: tuple(map(int, v.split("."))) if SEMVER.match(v) else (0, 0, 0))


def _source_hashes(src_dir: str | Path) -> dict[str, str]:
    src = Path(src_dir)
    return {name: hashlib.sha256((src / name).read_bytes()).hexdigest()
            for name in ("mappings.yaml", "metrics.osi.yaml") if (src / name).exists()}


def _published_mapping(lake: Store, version: str):
    """The mapping a published version rendered, or None when that version has no tables."""
    from ..structured.mapping import Mapping
    key = f"{layout.ontology_version_prefix(version)}/renditions/structured/mapping.json"
    if not lake.exists(key):
        return None
    return Mapping.from_json(json.loads(lake.get(key)))


def publish(lake: Store, src_dir: str | Path, *, by: str = "", note: str = "", activate: bool = False,
            force_full: bool = False) -> dict:
    """Publish the ontology in src_dir as the version its owl:versionInfo names."""
    from . import renditions
    spec, ttl, shapes = renditions.read_master(src_dir)
    from ..structured.mapping import change_kind, load as load_mapping
    mapping = load_mapping(src_dir, spec)
    version = spec.version
    if not SEMVER.match(version or ""):
        raise ValueError(f"owl:versionInfo must be a semver X.Y.Z, not {version!r}")
    if spec.is_empty():
        raise ValueError("the ontology declares no classes in its own namespace")
    if spec.version_iri and spec.version_iri.rstrip("/").rsplit("/", 1)[-1] != version:
        raise ValueError(f"owl:versionIRI <{spec.version_iri}> does not name version {version}; "
                         f"set it to <{spec.iri.rstrip('/')}/{version}> with owl:versionInfo")
    pre = layout.ontology_version_prefix(version)
    if lake.exists(f"{pre}/manifest.json"):
        raise ValueError(f"version {version} is already published, and published versions are immutable; "
                         "bump owl:versionInfo")
    base = active_version(lake)
    if base:
        old, _ = load_version(lake, base)
        d = diff(old, spec)
        old_mapping = _published_mapping(lake, base)
        mk, notes = change_kind(old_mapping, mapping)
        if d.kind == "none" and mk == "none":
            raise ValueError(f"{version} is identical to the active version {base}")
        onto_need, map_need = required_bump(d.kind), required_bump(mk)
        rank = {"none": -1, "patch": 0, "minor": 1, "major": 2}
        order = {"none": 0, "descriptive": 1, "additive": 2, "semantic": 3, "removal": 4}
        need = onto_need if rank[onto_need] >= rank[map_need] else map_need
        got = bump_of(base, version)
        if rank[got] < rank[need]:
            why = d.to_dict() if d.kind != "none" else {"mapping": notes}
            raise ValueError(f"{version} is a {got} bump over {base}, but the change needs a {need} bump: {why}")
        kind = d.kind if order[d.kind] >= order[mk] else mk
        if force_full and kind in ("additive", "descriptive"):
            kind = "semantic"
        changes = d.to_dict()
        if notes:
            changes["mapping"] = notes
        if d.kind == "none":
            changes["kind"] = kind
    else:
        kind, changes = "initial", {"kind": "initial", "added": sorted({**spec.classes, **spec.relations,
                                                                        **spec.attributes})}
        if mapping:
            _, notes = change_kind(None, mapping)
            changes["mapping"] = notes
    files = renditions.render_all(spec, ttl, shapes, mapping)
    types = {".ttl": "text/turtle", ".json": "application/json", ".jsonld": "application/ld+json",
             ".md": "text/markdown", ".cypher": "text/plain"}
    for rel, body in files.items():
        lake.put(f"{pre}/renditions/{rel}", body, types.get(Path(rel).suffix, "application/octet-stream"))
    lake.put(f"{pre}/ontology.ttl", ttl, "text/turtle")
    if shapes:
        lake.put(f"{pre}/shapes.ttl", shapes, "text/turtle")
    m = {"version": version, "base": base if kind not in FULL_KINDS else None, "kind": kind,
         "changes": changes, "delta_terms": changes.get("added", []) if kind == "additive" else [],
         "sha256": {"ontology.ttl": hashlib.sha256(ttl).hexdigest(),
                    **({"shapes.ttl": hashlib.sha256(shapes).hexdigest()} if shapes else {}),
                    **_source_hashes(src_dir)},
         "renditions": renditions.checksums(files),
         "published_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
         "published_by": by, "note": note,
         "counts": {"classes": len(spec.classes), "relations": len(spec.relations),
                    "attributes": len(spec.attributes)}}
    put_json(lake, f"{pre}/manifest.json", m)
    if activate:
        activate_version(lake, version)
    return m


def activate_version(lake: Store, version: str) -> None:
    manifest(lake, version)  # raises if it was never published
    put_json(lake, layout.ONTOLOGY_ACTIVE, {"version": version,
                                            "activated_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds")})
