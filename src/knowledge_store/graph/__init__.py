"""The graph projection: the active version's entities and relations in a graph database.

The portal's index answers everything from memory, which is right for tens of thousands of
entities. A graph backend holds the same entities and relations for collections beyond that,
and for other consumers of a property graph (Cypher agents, analysts). Like the index it is a
projection: rebuilt from gold, safe to drop. This package imports only the standard library at
load, so the portal Lambda can use it; each backend imports its driver.

    GRAPH_BACKEND   none (the default) | neo4j | age

A backend needs only to load a graph, drop one, list them, and answer two primitives: a node by
id, and the relations of a set of nodes (with their neighbours). Neighbourhoods and paths are
computed from those primitives in traverse.py, the same code for the in-memory index and every
backend, so they answer alike. A backend also filters by scope in its queries, and traverse.py
filters again.

Each load is a new graph, keyed by collection, version and build. The pipeline's load stage
(pipeline/load.py) fills it, checks its counts against the projection, then points the lake at
it (layout.GRAPH_POINTER); the portal reads a graph only when that pointer names the index it
is serving, and falls back to memory otherwise. The previous graph is kept for rollback, and
older ones are dropped.
"""

from __future__ import annotations

import os
import re
from typing import Protocol

_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def safe_name(name: str) -> str:
    """Labels and relationship types are written into query text (no engine takes them as
    parameters), so they must be plain identifiers. Ontology names are; this makes sure."""
    if not _NAME.match(name):
        raise ValueError(f"{name!r} is not a plain identifier, so it cannot be a graph label")
    return name


class Adjacency(Protocol):
    """What traverse.py needs from a graph. Node and neighbour dicts carry id, name, type,
    aliases, docs, links and scope; an edge carries s, o, p and scope."""

    def node(self, node_id: str) -> dict | None: ...
    def adjacent(self, ids: list[str], private: bool) -> list[tuple[dict, dict]]: ...


class GraphStore(Protocol):
    name: str          # the GRAPH_BACKEND value
    rendition: str     # the schema rendition it loads, under ontology/versions/<v>/renditions/

    def key_for(self, collection: str, version: str, built_at: str) -> str: ...
    def load(self, key: str, nodes: list[dict], edges: list[dict], schema: str) -> dict: ...
    def drop(self, key: str) -> None: ...
    def keys(self, collection: str) -> list[str]: ...
    def bind(self, key: str) -> Adjacency: ...


def from_env() -> GraphStore | None:
    kind = os.environ.get("GRAPH_BACKEND", "none")
    if kind == "none":
        return None
    if kind == "neo4j":
        from .neo4j import Neo4jStore
        return Neo4jStore.from_env()
    if kind == "age":
        from .age import AgeStore
        return AgeStore.from_env()
    raise ValueError(f"GRAPH_BACKEND must be none, neo4j or age, not {kind!r}")


_store: dict[str, GraphStore | None] = {}


def store() -> GraphStore | None:
    """The configured backend, one per process."""
    if "s" not in _store:
        _store["s"] = from_env()
    return _store["s"]


def stamp(built_at: str) -> str:
    """2026-09-30T12:34:56+00:00 -> 20260930123456"""
    return re.sub(r"\D", "", built_at)[:14]


def rows(entities: list[dict], passages: dict, spec, base: str) -> tuple[list[dict], list[dict]]:
    """Nodes and edges from the projection (the entities and passages project() writes), in the
    shape the neo4j/mapping.json rendition describes. (Imported here, not at the top: the portal
    Lambda imports this package and ships without rdflib, which renditions needs.)"""
    from ..ontology.renditions import label_of, property_of, rel_type

    def public(pids) -> bool:
        return any(passages.get(p, {}).get("scope") == "public" for p in pids)

    nodes, edges = [], []
    for e in entities:
        types = sorted({a for t in e["types"] if t in spec.classes for a in spec.ancestors(t)} | set(e["types"]))
        props = {"id": e["id"], "iri": base + e["id"], "name": e["label"], "type": e["type"], "types": types,
                 "aliases": list(e["aliases"]), "scope": e.get("scope", "public"), "docs": len(e["docs"]),
                 "links": len(e["out"]) + len(e["in"]), "mentioned_in": list(e["passages"])}
        for a in e["attributes"]:
            k = property_of(a["p"])
            props.setdefault(k, []).append(a["v"])
            cited = props.setdefault(f"{k}__passages", [])
            cited.extend(p for p in a["passages"] if p not in cited)
        nodes.append({"labels": ["Entity", *(safe_name(label_of(t)) for t in types)], "props": props})
        for r in e["out"]:
            edges.append({"s": e["id"], "o": r["o"], "type": safe_name(rel_type(r["p"])),
                          "props": {"p": r["p"], "passages": list(r["passages"]),
                                    "scope": "public" if public(r["passages"]) else "private"}})
    return nodes, edges
