"""The configured graph backend: GRAPH_BACKEND picks the GraphStore adapter, one per process.

    GRAPH_BACKEND   none (the default) | neo4j | age
"""

from __future__ import annotations

import os

from knowledge_store.knowledge_graph.ports import GraphStore


def from_env() -> GraphStore | None:
    kind = os.environ.get("GRAPH_BACKEND", "none")
    if kind == "none":
        return None
    if kind == "neo4j":
        from knowledge_store.knowledge_graph.adapters.neo4j import Neo4jStore
        return Neo4jStore.from_env()
    if kind == "age":
        from knowledge_store.knowledge_graph.adapters.age import AgeStore
        return AgeStore.from_env()
    raise ValueError(f"GRAPH_BACKEND must be none, neo4j or age, not {kind!r}")


_store: dict[str, GraphStore | None] = {}


def store() -> GraphStore | None:
    """The configured backend, one per process."""
    if "s" not in _store:
        _store["s"] = from_env()
    return _store["s"]
