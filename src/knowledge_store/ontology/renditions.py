"""Master and renditions: one authoritative ontology, many derived forms, generated at release.

The master is the curated source in git: OWL and SHACL in Turtle today (a reader for another
master format registers in MASTERS). Nothing downstream is edited by hand. Every published
version renders the master into forms for each consumer, stored beside it in the lake
(ontology/versions/<v>/renditions/) and listed with checksums in the manifest:

    owl/ontology.ttl, owl/shapes.ttl     the formal model, for SPARQL stores (Neptune), SHACL
                                         validation and the pipeline itself
    agent/ontology.md                    a compact vocabulary to put in an agent's prompt
    agent/ontology.json                  the same as data: types, relations, attributes, synonyms
    neo4j/schema.cypher                  constraints and indexes for a property-graph projection
    neo4j/mapping.json                   class -> label, relation -> relationship type, attribute
                                         -> property: the contract an RDF-to-LPG loader follows
    neo4j/schema.md                      the graph schema as (:A)-[:REL]->(:B), for Cypher agents
    age/schema.sql                       the same projection in PostgreSQL with Apache AGE: the graph,
                                         its labels and indexes, for a graph name the loader fills in
    spanner/schema.sql                   the node and edge tables and the property graph for Spanner Graph
    extraction/tool.json                 the JSON Schema of the extraction tool call
    jsonld/context.jsonld                a JSON-LD context mapping term names to IRIs

Because every rendition is a pure function of the master, two releases of the same master give
identical renditions, and a rendition can always be regenerated. A consumer pins a version and
reads the rendition it needs, never the master.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Callable

from rdflib import Graph

from . import model

# --- master readers ----------------------------------------------------------------------------


def read_turtle(src: Path) -> tuple[model.OntologySpec, bytes, bytes | None]:
    ttl = (src / "ontology.ttl").read_bytes()
    shapes = (src / "shapes.ttl").read_bytes() if (src / "shapes.ttl").exists() else None
    return model.load(data=ttl.decode()), ttl, shapes


MASTERS: dict[str, Callable[[Path], tuple[model.OntologySpec, bytes, bytes | None]]] = {"turtle": read_turtle}


def read_master(src: str | Path) -> tuple[model.OntologySpec, bytes, bytes | None]:
    src = Path(src)
    fmt = "turtle" if (src / "ontology.ttl").exists() else None
    if fmt is None:
        raise ValueError(f"{src}: no master ontology found (expected ontology.ttl)")
    return MASTERS[fmt](src)


# --- naming for property graphs -----------------------------------------------------------------


def rel_type(local: str) -> str:
    """launchedBy -> LAUNCHED_BY"""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", local).upper()


def label_of(local: str) -> str:
    return local[:1].upper() + local[1:]


# --- renderers ----------------------------------------------------------------------------------


def _agent_md(spec: model.OntologySpec) -> str:
    lines = [f"# {spec.label or 'Ontology'} {spec.version}", "",
             "Types, relations and attributes of the knowledge graph. Names on the left are what queries and tools use.", "",
             "## Types"]
    kids: dict[str, list[str]] = {}
    for c in spec.classes.values():
        for p in c.parents or ("",):
            kids.setdefault(p, []).append(c.local)

    def walk(parent: str, depth: int) -> None:
        for local in sorted(kids.get(parent, [])):
            c = spec.classes[local]
            syn = f" (also: {', '.join(c.alt_labels)})" if c.alt_labels else ""
            lines.append(f"{'  ' * depth}- {c.local}: {c.definition or c.label}{syn}")
            walk(local, depth + 1)

    walk("", 0)
    if spec.relations:
        lines += ["", "## Relations (subject -> object)"]
        for p in sorted(spec.relations.values(), key=lambda t: t.local):
            lines.append(f"- {p.local}: {'|'.join(p.domain) or 'any'} -> {'|'.join(p.range) or 'any'}. {p.definition}".rstrip())
    if spec.attributes:
        lines += ["", "## Attributes"]
        for p in sorted(spec.attributes.values(), key=lambda t: t.local):
            lines.append(f"- {p.local} ({p.range[0] if p.range else 'string'}) of {'|'.join(p.domain) or 'any'}. {p.definition}".rstrip())
    return "\n".join(lines) + "\n"


def _agent_json(spec: model.OntologySpec) -> dict:
    return {"version": spec.version, "namespace": spec.namespace, "label": spec.label,
            "types": [{"name": c.local, "label": c.label, "definition": c.definition, "synonyms": list(c.alt_labels),
                       "parents": list(c.parents)} for c in sorted(spec.classes.values(), key=lambda t: t.local)],
            "relations": [{"name": p.local, "label": p.label, "definition": p.definition, "synonyms": list(p.alt_labels),
                           "domain": list(p.domain), "range": list(p.range)}
                          for p in sorted(spec.relations.values(), key=lambda t: t.local)],
            "attributes": [{"name": p.local, "label": p.label, "definition": p.definition, "synonyms": list(p.alt_labels),
                            "domain": list(p.domain), "datatype": p.range[0] if p.range else "string"}
                           for p in sorted(spec.attributes.values(), key=lambda t: t.local)]}


def _neo4j_mapping(spec: model.OntologySpec) -> dict:
    return {
        "version": spec.version,
        "node_key": "id",
        "graph_key": "g",
        "entity_label": "Entity",
        "labels": {c.local: {"label": label_of(c.local), "iri": c.iri,
                             "also": sorted(label_of(a) for a in spec.ancestors(c.local) - {c.local})}
                   for c in spec.classes.values()},
        "relationships": {p.local: {"type": rel_type(p.local), "iri": p.iri, "from": list(p.domain), "to": list(p.range)}
                          for p in spec.relations.values()},
        "properties": {p.local: {"property": property_of(p.local), "iri": p.iri, "datatype": p.range[0] if p.range else "string",
                                 "on": list(p.domain)} for p in spec.attributes.values()},
        "provenance": {"passages": "each relationship and each attribute carries passage ids in a `passages` list "
                                   "property (attributes as `<property>__passages`); entities carry `mentioned_in`"},
        "node_properties": {"id": "the entity id (its IRI without the data base)", "iri": "the RDF IRI",
                            "name": "rdfs:label", "type": "the most specific class",
                            "types": "every class, ancestors included", "aliases": "skos:altLabel",
                            "scope": "public if any document it is in is public", "docs": "documents it is in",
                            "links": "relations in and out", "mentioned_in": "passage ids"},
        "reserved": sorted(RESERVED),
        "notes": "A node carries the label of its class and of every ancestor, so a query on a parent class finds its "
                 "subclasses' nodes. Several graphs can share one database, told apart by `g` (collection, version "
                 "and build), so a node is unique on (g, id). An attribute whose name is reserved is stored as "
                 "`a_<name>`. Every relationship carries `p` (the relation's name) and `scope` (public if any "
                 "passage it cites is public). The graph is rebuilt from the record, never edited.",
    }


# Node properties the projection writes itself; an attribute with one of these names is stored as a_<name>.
RESERVED = frozenset({"g", "id", "iri", "name", "type", "types", "aliases", "scope", "docs", "links", "mentioned_in"})


def property_of(attribute: str) -> str:
    return f"a_{attribute}" if attribute in RESERVED else attribute


def _neo4j_cypher(spec: model.OntologySpec) -> str:
    out = [f"// Generated from the master ontology {spec.version}. Do not edit: regenerate from the master.",
           "CREATE CONSTRAINT entity_key IF NOT EXISTS FOR (n:Entity) REQUIRE (n.g, n.id) IS UNIQUE;",
           "CREATE INDEX entity_g IF NOT EXISTS FOR (n:Entity) ON (n.g);",
           "CREATE INDEX entity_iri IF NOT EXISTS FOR (n:Entity) ON (n.iri);",
           "CREATE INDEX entity_name IF NOT EXISTS FOR (n:Entity) ON (n.name);"]
    for c in sorted(spec.classes.values(), key=lambda t: t.local):
        lab = label_of(c.local)
        out.append(f"CREATE INDEX {c.local.lower()}_name IF NOT EXISTS FOR (n:{lab}) ON (n.name);")
    for p in sorted(spec.attributes.values(), key=lambda t: t.local):
        for d in p.domain:
            out.append(f"CREATE INDEX {d.lower()}_{p.local.lower()} IF NOT EXISTS FOR (n:{label_of(d)}) "
                       f"ON (n.{property_of(p.local)});")
    return "\n".join(out) + "\n"


def _age_sql(spec: model.OntologySpec) -> str:
    """AGE gives a vertex one label, so every node is :Entity and its classes are in `types`; a
    query on a class tests membership of `types`. Each relation is an edge label. {graph} is the
    graph's name, filled in by the loader: AGE keeps each loaded graph as a graph of its own."""
    out = [f"-- Generated from the master ontology {spec.version}. Do not edit: regenerate from the master.",
           "-- {graph} is the graph name; the loader fills it in.",
           "SELECT create_graph('{graph}');",
           "SELECT create_vlabel('{graph}', 'Entity');",
           'CREATE INDEX ON "{graph}"."Entity" USING gin (properties);',
           'CREATE UNIQUE INDEX ON "{graph}"."Entity" '
           "(ag_catalog.agtype_access_operator(VARIADIC ARRAY[properties, '\"id\"'::agtype]));"]
    for p in sorted(spec.relations.values(), key=lambda t: t.local):
        t = rel_type(p.local)
        out += [f"SELECT create_elabel('{{graph}}', '{t}');",
                f'CREATE INDEX ON "{{graph}}"."{t}" (start_id);',
                f'CREATE INDEX ON "{{graph}}"."{t}" (end_id);']
    return "\n".join(out) + "\n"


def _spanner_sql(spec: model.OntologySpec) -> str:
    """Spanner Graph maps tables to a property graph. The tables do not depend on the ontology
    (classes are in `types`, relations in `p`, attributes in `attributes`), so a release never
    needs a schema change. Graphs are told apart by `g`."""
    return f"""-- Generated from the master ontology {spec.version}. Do not edit: regenerate from the master.
CREATE TABLE Entity (
  g STRING(256) NOT NULL,
  id STRING(1024) NOT NULL,
  iri STRING(MAX),
  name STRING(MAX),
  type STRING(MAX),
  types ARRAY<STRING(MAX)>,
  aliases ARRAY<STRING(MAX)>,
  scope STRING(16),
  docs INT64,
  links INT64,
  mentioned_in ARRAY<STRING(MAX)>,
  attributes JSON,
) PRIMARY KEY (g, id);

CREATE TABLE Relation (
  g STRING(256) NOT NULL,
  id STRING(1024) NOT NULL,
  p STRING(256) NOT NULL,
  o STRING(1024) NOT NULL,
  passages ARRAY<STRING(MAX)>,
  scope STRING(16),
) PRIMARY KEY (g, id, p, o),
  INTERLEAVE IN PARENT Entity ON DELETE CASCADE;

CREATE INDEX RelationByObject ON Relation (g, o);

CREATE PROPERTY GRAPH KnowledgeGraph
  NODE TABLES (Entity KEY (g, id) LABEL Entity PROPERTIES ALL COLUMNS)
  EDGE TABLES (
    Relation KEY (g, id, p, o)
      SOURCE KEY (g, id) REFERENCES Entity (g, id)
      DESTINATION KEY (g, o) REFERENCES Entity (g, id)
      LABEL Relation PROPERTIES ALL COLUMNS
  );
"""


def _neo4j_md(spec: model.OntologySpec) -> str:
    lines = [f"# Graph schema {spec.version}", "", "Node labels (every node is also :Entity, with name, iri):"]
    for c in sorted(spec.classes.values(), key=lambda t: t.local):
        par = f" (also :{', :'.join(label_of(a) for a in sorted(spec.ancestors(c.local) - {c.local}))})" \
            if spec.ancestors(c.local) - {c.local} else ""
        props = [p.local for p in spec.attributes.values() if not p.domain or any(spec.is_a(c.local, d) for d in p.domain)]
        lines.append(f"- :{label_of(c.local)}{par}" + (f" {{{', '.join(sorted(props))}}}" if props else ""))
    if spec.relations:
        lines += ["", "Relationships:"]
        for p in sorted(spec.relations.values(), key=lambda t: t.local):
            for d in p.domain or ("Entity",):
                for r in p.range or ("Entity",):
                    lines.append(f"- (:{label_of(d)})-[:{rel_type(p.local)}]->(:{label_of(r)})")
    return "\n".join(lines) + "\n"


def _jsonld_context(spec: model.OntologySpec) -> dict:
    ctx: dict = {"@vocab": spec.namespace, "ks": str(model.KL), "name": "http://www.w3.org/2000/01/rdf-schema#label"}
    for c in spec.classes.values():
        ctx[c.local] = c.iri
    for p in spec.relations.values():
        ctx[p.local] = {"@id": p.iri, "@type": "@id"}
    for p in spec.attributes.values():
        kind = p.range[0] if p.range else "string"
        ctx[p.local] = {"@id": p.iri, **({"@type": str(model.DATATYPES[kind])} if kind != "string" else {})}
    return {"@context": ctx}


def _owl(spec: model.OntologySpec, ttl: bytes) -> bytes:
    return ttl


SCHEMAS = {"neo4j/schema.cypher": _neo4j_cypher, "age/schema.sql": _age_sql, "spanner/schema.sql": _spanner_sql}


def render_schema(spec: model.OntologySpec, path: str) -> str:
    """One graph schema rendition, for a version released before that rendition existed."""
    return SCHEMAS[path](spec)


def render_all(spec: model.OntologySpec, ttl: bytes, shapes: bytes | None) -> dict[str, bytes]:
    from ..extract.schema import tool_spec
    j = lambda o: (json.dumps(o, indent=2, sort_keys=False) + "\n").encode()  # noqa: E731
    out = {
        "owl/ontology.ttl": _owl(spec, ttl),
        "agent/ontology.md": _agent_md(spec).encode(),
        "agent/ontology.json": j(_agent_json(spec)),
        "neo4j/schema.cypher": _neo4j_cypher(spec).encode(),
        "neo4j/mapping.json": j(_neo4j_mapping(spec)),
        "neo4j/schema.md": _neo4j_md(spec).encode(),
        "age/schema.sql": _age_sql(spec).encode(),
        "spanner/schema.sql": _spanner_sql(spec).encode(),
        "extraction/tool.json": j(tool_spec(spec)),
        "jsonld/context.jsonld": j(_jsonld_context(spec)),
    }
    if shapes:
        Graph().parse(data=shapes.decode(), format="turtle")  # a release never ships shapes that do not parse
        out["owl/shapes.ttl"] = shapes
    return out


def checksums(files: dict[str, bytes]) -> dict[str, str]:
    return {k: hashlib.sha256(v).hexdigest() for k, v in sorted(files.items())}


def write_local(files: dict[str, bytes], out_dir: str | Path) -> list[Path]:
    paths = []
    for rel, body in files.items():
        p = Path(out_dir) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(body)
        paths.append(p)
    return paths
