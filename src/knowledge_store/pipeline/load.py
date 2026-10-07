"""Load: the projection -> the graph backend (GRAPH_BACKEND) and the document store
(PROJECTION_STORE), when either is configured; the gold graphs -> the SPARQL store (Neptune, when
NEPTUNE_ENDPOINT is set); the passages -> the Knowledge Base (when KNOWLEDGE_BASE_ID is set).

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
import json
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


# --- the SPARQL store (Neptune) ---------------------------------------------------------------

ONTOLOGY_GRAPH = "graph/ontology"   # under the collection's data base: <base>graph/ontology
INSERT_BATCH = 2000                  # triples per INSERT DATA block (one request per graph)


def sparql_client():
    from ..graph import sparql
    return sparql.client_from_env()


def _graphs(lake: Store, version: str, spec) -> dict[str, tuple[str, str]]:
    """graph IRI -> (content hash, N-Triples) for every named graph the active chain holds, and
    the active ontology's T-Box. Each gold file holds one document's graph at one version."""
    from rdflib import Dataset, Graph
    out = {}
    for v in versions.chain(lake, version):
        for key, etag in lake.objects(f"{layout.gold_prefix(v)}/graph/"):
            if not key.endswith(".nq"):
                continue
            ds = Dataset()
            ds.parse(data=lake.get(key).decode(), format="nquads")
            for ctx in ds.graphs():
                if len(ctx):
                    out[str(ctx.identifier)] = (f"{v}:{etag}", ctx.serialize(format="nt"))
    ttl = lake.get(f"{layout.ontology_version_prefix(version)}/ontology.ttl")
    t = Graph().parse(data=ttl.decode(), format="turtle")
    out[data_base(spec) + ONTOLOGY_GRAPH] = (f"{version}:{layout.sha256(ttl)}", t.serialize(format="nt"))
    return out


def _replace(client, g: str, nt: str) -> int:
    from ..graph.sparql import iri
    lines = [ln for ln in nt.splitlines() if ln.strip()]
    blocks = [f"INSERT DATA {{ GRAPH {iri(g)} {{\n" + "\n".join(lines[i:i + INSERT_BATCH]) + "\n} }"
              for i in range(0, len(lines), INSERT_BATCH)]
    client.update(" ;\n".join([f"DROP SILENT GRAPH {iri(g)}", *blocks]))  # one request: one transaction
    n = client.select(f"SELECT (COUNT(*) AS ?n) WHERE {{ GRAPH {iri(g)} {{ ?s ?p ?o }} }}")
    got = int(n[0]["n"][1]) if n else 0
    if got != len(lines):
        raise RuntimeError(f"graph {g}: loaded {got} triples, expected {len(lines)}")
    return got


def load_sparql(lake: Store, client=None) -> dict | None:
    """Keep the SPARQL store in step with the lake: replace each named graph whose source changed,
    drop the collection's graphs that left the active chain. Each graph is replaced in a single
    update, so a reader sees a document's old facts or its new ones, never a mix; during a load
    the store can hold some documents at the new build and some at the old."""
    from ..graph.sparql import iri, lit
    client = client or sparql_client()
    version = versions.active_version(lake)
    if client is None or not version or not lake.exists(layout.index_key(version, "summary")):
        return None
    built = get_json(lake, layout.index_key(version, "summary"))["built_at"]
    current = get_json(lake, layout.SPARQL_POINTER) if lake.exists(layout.SPARQL_POINTER) else {}
    if (current.get("version"), current.get("built_at")) == (version, built):
        return current
    spec, _ = versions.load_version(lake, version)
    base = data_base(spec)
    want = _graphs(lake, version, spec)
    held = {r["g"][1] for r in client.select(
        f"SELECT DISTINCT ?g WHERE {{ GRAPH ?g {{ ?s ?p ?o }} FILTER(STRSTARTS(STR(?g), {lit(base + 'graph/')})) }}")}
    loaded = dict(current.get("graphs") or {})
    triples = replaced = 0
    for g in sorted(want, key=lambda g: (g != base + ONTOLOGY_GRAPH, g)):  # the T-Box first
        h, nt = want[g]
        if loaded.get(g) == h and g in held:
            continue
        triples += _replace(client, g, nt)
        replaced += 1
        loaded[g] = h
    dropped = sorted(held - set(want))
    for g in dropped:
        client.update(f"DROP SILENT GRAPH {iri(g)}")
    new = {"key": f"{version}@{built}", "version": version, "built_at": built,
           "graphs": {g: loaded[g] for g in want},
           "counts": {"graphs": len(want), "replaced": replaced, "triples_loaded": triples, "dropped": len(dropped)},
           "loaded_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds")}
    put_json(lake, layout.SPARQL_POINTER, new)
    log.info("sparql store: %s", new["counts"])
    return new


# --- the Knowledge Base's passages ----------------------------------------------------------------

def knowledge_base() -> tuple[str, str] | None:
    kb, ds = os.environ.get("KNOWLEDGE_BASE_ID"), os.environ.get("KNOWLEDGE_BASE_DATA_SOURCE_ID")
    return (kb, ds) if kb and ds else None


def start_ingestion(kb: tuple[str, str]) -> str | None:
    import boto3
    client = boto3.client("bedrock-agent")
    try:
        return client.start_ingestion_job(knowledgeBaseId=kb[0], dataSourceId=kb[1])["ingestionJob"]["ingestionJobId"]
    except client.exceptions.ConflictException:  # one is running; the next sweep starts another
        return None


def sync_passages(lake: Store, kb=None, start=None) -> dict | None:
    """Every passage of every refined document, one file each with its metadata, under
    kb/passages/<collection>/ at the lake's root, which the Knowledge Base's data source reads;
    then an ingestion job when anything changed. One passage is one vector (chunking NONE), so a
    search hit is a passage id, the same id the graph's citations use."""
    from .refine import load_doc, load_passages, silver_doc_ids
    kb = kb or knowledge_base()
    if kb is None:
        return None
    start = start or start_ingestion
    cid = collections.collection_id(lake) or collections.DEFAULT_ID
    root = getattr(lake, "whole", lake)
    prefix = f"{layout.KB_PASSAGES}/{cid}/"
    current = get_json(lake, layout.PASSAGES_POINTER) if lake.exists(layout.PASSAGES_POINTER) else {}
    held: dict = dict(current.get("files") or {})
    want: dict[str, str] = {}
    written = 0
    for doc_id in sorted(silver_doc_ids(lake)):
        doc = load_doc(lake, doc_id)
        title = (doc.get("title") or doc.get("name") or "")[:300]
        scope = doc.get("scope", "public")
        for p in load_passages(lake, doc_id):
            h = layout.sha256(f"{p.text}\x00{scope}\x00{title}".encode())[:16]
            want[p.passage_id] = h
            if held.get(p.passage_id) == h:
                continue
            meta = {"metadataAttributes": {"passage_id": p.passage_id, "doc": doc_id, "collection": cid,
                                           "scope": scope, "title": title, "source_uri": doc.get("source_uri") or ""}}
            root.put(f"{prefix}{p.passage_id}.txt", p.text.encode(), "text/plain; charset=utf-8")
            root.put(f"{prefix}{p.passage_id}.txt.metadata.json", json.dumps(meta).encode(), "application/json")
            written += 1
    removed = sorted(set(held) - set(want))
    for pid in removed:
        root.delete(f"{prefix}{pid}.txt")
        root.delete(f"{prefix}{pid}.txt.metadata.json")
    pending = bool(written or removed or current.get("pending"))
    if not pending and current:
        return current
    job = start(kb) if pending else None
    now = dt.datetime.now(dt.UTC).isoformat(timespec="seconds")
    new = {"key": f"{len(want)}@{now}", "files": want, "pending": pending and job is None,
           "ingestion_job": job or current.get("ingestion_job"),
           "counts": {"passages": len(want), "written": written, "removed": len(removed)}, "synced_at": now}
    put_json(lake, layout.PASSAGES_POINTER, new)
    log.info("knowledge base passages: %s, ingestion job %s", new["counts"], job)
    return new
