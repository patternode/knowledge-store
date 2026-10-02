"""Load: the projection -> the graph backend (GRAPH_BACKEND) and the document store
(PROJECTION_STORE), when either is configured.

Runs at the end of every sweep, and does nothing unless the graph the lake points at is not the
one for the index being served: after a new projection, after a failed load, or when a backend is
first configured. So the sweep stays the recovery path.

A load goes into a new graph. Its node and edge counts are checked against the projection before
the lake's pointer (layout.GRAPH_POINTER) moves to it, and the portal reads the graph only while
the pointer names the index it serves; until then it answers from memory. The graph before is
kept for rollback (set the pointer back); older ones are dropped.
"""

from __future__ import annotations

import datetime as dt
import logging
import os

from .. import collections, graph, layout
from ..extract.rdf import data_base
from ..ontology import renditions, versions
from ..store import Store, get_json, put_json

log = logging.getLogger("load")


def pointer(lake: Store) -> dict:
    return get_json(lake, layout.GRAPH_POINTER) if lake.exists(layout.GRAPH_POINTER) else {}


def schema(lake: Store, spec, version: str, path: str) -> str:
    key = f"{layout.ontology_version_prefix(version)}/renditions/{path}"
    return lake.get(key).decode() if lake.exists(key) else renditions.render_schema(spec, path)


def load_graph(lake: Store, store=None) -> dict | None:
    store = store or graph.store()
    version = versions.active_version(lake)
    if store is None or not version or not lake.exists(layout.index_key(version, "summary")):
        return None
    built = get_json(lake, layout.index_key(version, "summary"))["built_at"]
    current = pointer(lake)
    if (current.get("backend"), current.get("version"), current.get("built_at")) == (store.name, version, built):
        return current
    cid = collections.collection_id(lake) or collections.DEFAULT_ID
    spec, _ = versions.load_version(lake, version)
    nodes, edges = graph.rows(get_json(lake, layout.index_key(version, "entities")),
                              get_json(lake, layout.index_key(version, "passages")), spec, data_base(spec))
    key = store.key_for(cid, version, built)
    store.drop(key)  # what an interrupted attempt left
    counts = store.load(key, nodes, edges, schema(lake, spec, version, store.rendition))
    expected = {"nodes": len(nodes), "edges": len(edges)}
    if counts != expected:
        store.drop(key)
        raise RuntimeError(f"graph load of {version} counted {counts}, expected {expected}")
    previous = current.get("key") if current.get("backend") == store.name else None
    new = {"backend": store.name, "key": key, "version": version, "built_at": built, "counts": counts,
           "loaded_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"), "previous": previous}
    put_json(lake, layout.GRAPH_POINTER, new)
    for k in store.keys(cid):
        if k not in (key, previous):
            store.drop(k)
    log.info("graph %s loaded for %s: %d nodes, %d edges", key, version, counts["nodes"], counts["edges"])
    return new


def document_store():
    """The document store for the portal's projection, if PROJECTION_STORE=mongodb."""
    if os.environ.get("PROJECTION_STORE", "memory") != "mongodb":
        return None
    from ..portal_api.docstore import connect
    return connect(os.environ["MONGODB_URI"], os.environ.get("MONGODB_DB", "knowledge_store"))


def load_documents(lake: Store, db=None) -> dict | None:
    """The projection -> the document store, on the same terms as load_graph."""
    from ..portal_api import docstore
    db = db if db is not None else document_store()
    version = versions.active_version(lake)
    if db is None or not version or not lake.exists(layout.index_key(version, "summary")):
        return None
    built = get_json(lake, layout.index_key(version, "summary"))["built_at"]
    current = get_json(lake, layout.DOCUMENTS_POINTER) if lake.exists(layout.DOCUMENTS_POINTER) else {}
    if (current.get("version"), current.get("built_at")) == (version, built):
        return current
    cid = collections.collection_id(lake) or collections.DEFAULT_ID
    entities = get_json(lake, layout.index_key(version, "entities"))
    passages = get_json(lake, layout.index_key(version, "passages"))
    docs = get_json(lake, layout.index_key(version, "docs"))
    key = docstore.key_for(cid, version, built)
    counts = docstore.load(db, key, entities, passages, docs)
    expected = {"entities": len(entities), "passages": len(passages), "docs": len(docs)}
    if counts != expected:
        docstore.drop(db, key)
        raise RuntimeError(f"document load of {version} counted {counts}, expected {expected}")
    previous = current.get("key")
    new = {"key": key, "version": version, "built_at": built, "counts": counts,
           "loaded_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"), "previous": previous}
    put_json(lake, layout.DOCUMENTS_POINTER, new)
    for k in docstore.keys(db, cid):
        if k not in (key, previous):
            docstore.drop(db, k)
    log.info("documents %s loaded for %s: %s", key, version, counts)
    return new
