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
(knowledge_graph/adapters/loading.py) fills it, checks its counts against the projection, then points the lake at
it (layout.GRAPH_POINTER); the portal reads a graph only when that pointer names the index it
is serving, and falls back to memory otherwise. The previous graph is kept for rollback, and
older ones are dropped.
"""

from __future__ import annotations

from typing import Protocol

from knowledge_store.kernel.identifiers import safe_name  # noqa: F401  (re-exported)


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


class ReadModel(Protocol):
    """The projection as the tools and the portal read it, filtered by scope. The in-memory index
    (adapters.index.Index), the document store (adapters.docstore.DocIndex) and the SPARQL store
    (adapters.sparql.SparqlIndex) implement it, so a tool answers alike whichever serves it."""

    version: str
    summary: dict

    def visible(self, item: dict, private: bool) -> bool: ...
    def entity_view(self, e: dict, private: bool) -> dict: ...
    def summary_view(self, private: bool) -> dict: ...
    def ontology_view(self, private: bool) -> dict: ...
    def search_entities(self, q: str = "", type_: str | None = None, *, private: bool, limit: int = 25) -> dict: ...
    def search_passages(self, q: str, *, private: bool, limit: int = 6) -> list[dict]: ...
    def passage_view(self, pid: str) -> dict: ...
    def neighbourhood(self, focus: str, *, hops: int = 1, private: bool, limit: int = 40) -> dict: ...
    def paths(self, source: str, target: str, *, max_hops: int = 3, private: bool, limit: int = 10) -> dict: ...


class SparqlStore(Protocol):
    """A SPARQL endpoint holding the gold graphs: Neptune (adapters.sparql.NeptuneClient) or an
    in-process rdflib dataset (adapters.sparql.LocalClient)."""

    def select(self, query: str) -> list[dict[str, tuple[str, str]]]: ...
    def update(self, update: str) -> None: ...


class PassageSearch(Protocol):
    """Search over a collection's passages, in the caller's scope: by meaning (the Bedrock
    Knowledge Base, adapters.passages.KnowledgeBaseSearch) or by keyword over the projection
    (adapters.passages.KeywordSearch)."""

    method: str

    def search(self, collection: str, query: str, *, private: bool, limit: int = 6) -> list[dict]: ...

