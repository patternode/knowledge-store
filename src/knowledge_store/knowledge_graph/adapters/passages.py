"""The passage tools' two sources: the Knowledge Base for search, the lake for text.

search   the Bedrock Knowledge Base (vectors in S3 Vectors) when KNOWLEDGE_BASE_ID is set: one
         vector per passage, filtered to the collection and, for a caller outside the private
         scope, to public passages. Without one, the vectors `knowledge-store embed` wrote to the
         lake (slices/embed.py), over every silver passage. Without those, keyword search over the
         projection's passages.
read     the passage's text from the projection, or from the silver layer for a passage no fact
         cites (a search hit can be one). The caller's scope is checked against the document's.

A passage id begins with the first 16 characters of its document's id (ingestion/domain/chunk.py), which
is how a passage is found in silver without an index.
"""

from __future__ import annotations

import operator
import os
import time

from knowledge_store.knowledge_graph.adapters.embeddings import embedder_from_env
from knowledge_store.knowledge_graph.slices.embed import read_vectors
from knowledge_store.platform_services import layout

VECTORS_CACHE_S = 60
_vectors: dict = {}

PASSAGE_ID_PREFIX = 16


def knowledge_base_id() -> str | None:
    return os.environ.get("KNOWLEDGE_BASE_ID") or None


def kb_search(cid: str, query: str, *, private: bool, limit: int = 6, client=None) -> list[dict]:
    if client is None:
        import boto3
        client = boto3.client("bedrock-agent-runtime")
    flt: dict = {"equals": {"key": "collection", "value": cid}}
    if not private:
        flt = {"andAll": [flt, {"equals": {"key": "scope", "value": "public"}}]}
    r = client.retrieve(knowledgeBaseId=knowledge_base_id(), retrievalQuery={"text": query[:1000]},
                        retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": limit, "filter": flt}})
    out = []
    for hit in r.get("retrievalResults", []):
        md = hit.get("metadata") or {}
        if md.get("collection") != cid or not (private or md.get("scope") == "public"):
            continue  # the filter should have done this; never trust one check alone
        out.append({"id": md.get("passage_id"), "doc": md.get("doc"), "title": md.get("title"),
                    "text": (hit.get("content") or {}).get("text", ""), "score": round(hit.get("score") or 0, 4),
                    "source_uri": md.get("source_uri") or None})
    return out


def from_silver(lake, ids: list[str], *, private: bool) -> list[dict]:
    """Passages by id from the silver layer, in the caller's scope."""
    from knowledge_store.ingestion import load_doc, load_passages
    prefixes = {i[:PASSAGE_ID_PREFIX] for i in ids}
    docs = [layout.doc_id_from_key(k) for k in lake.list(layout.SILVER_DOCS + "/") if k.endswith(".json")]
    want, out = set(ids), []
    for d in docs:
        if d[:PASSAGE_ID_PREFIX] not in prefixes:
            continue
        doc = load_doc(lake, d)
        if not (private or doc.get("scope", "public") == "public"):
            continue
        for p in load_passages(lake, d):
            if p.passage_id in want:
                out.append({"id": p.passage_id, "doc": d, "title": doc.get("title") or doc.get("name"),
                            "text": p.text, "seq": p.seq, "source_uri": doc.get("source_uri"),
                            "name": doc.get("name")})
    return out


def read(lake, idx, ids: list[str], *, private: bool) -> list[dict]:
    ids = [i for i in dict.fromkeys(ids or []) if isinstance(i, str)][:10]
    found = {}
    if idx is not None:
        for p in ids:
            if p in idx.passages and idx.visible(idx.passages[p], private):
                v = idx.passage_view(p)
                d = idx.docs.get(v["doc"]) or {}
                v["source_uri"], v["name"] = d.get("source_uri"), d.get("name")
                found[p] = v
    missing = [p for p in ids if p not in found]
    if missing:
        for v in from_silver(lake, missing, private=private):
            found[v["id"]] = v
    return [found[p] for p in ids if p in found]


class KnowledgeBaseSearch:
    """PassageSearch by meaning, over the Bedrock Knowledge Base."""

    method = "vector"

    def __init__(self, client=None):
        self.client = client

    def search(self, collection: str, query: str, *, private: bool, limit: int = 6) -> list[dict]:
        return kb_search(collection, query, private=private, limit=limit, client=self.client)


class KeywordSearch:
    """PassageSearch by keyword, over the projection's passages."""

    method = "keyword"

    def __init__(self, idx):
        self.idx = idx

    def search(self, collection: str, query: str, *, private: bool, limit: int = 6) -> list[dict]:
        return self.idx.search_passages(query, private=private, limit=limit)


def _lake_key(lake) -> tuple:
    return tuple(sorted((k, str(v)) for k, v in vars(lake).items() if isinstance(v, (str, os.PathLike))))


def vectors_of(lake) -> list[dict]:
    """The embedded passages of a lake, cached for a minute."""
    key = _lake_key(lake)
    hit = _vectors.get(key)
    if hit is None or time.monotonic() - hit[0] > VECTORS_CACHE_S:
        hit = _vectors[key] = (time.monotonic(), read_vectors(lake)[1])
    return hit[1]


def has_vectors(lake) -> bool:
    return lake is not None and lake.exists(layout.SILVER_VECTORS)


class LocalVectorSearch:
    """PassageSearch by meaning, over the vectors embed_passages wrote to the lake: every silver
    passage, not only those a fact cites, scored by cosine (the vectors are normalised)."""

    method = "vector"

    def __init__(self, lake, embedder=None):
        self.lake, self.embedder = lake, embedder or embedder_from_env()

    def search(self, collection: str, query: str, *, private: bool, limit: int = 6) -> list[dict]:
        q = self.embedder.embed([(query or "")[:1000]])[0]
        scored = []
        for r in vectors_of(self.lake):
            if private or r.get("scope", "public") == "public":
                scored.append((sum(map(operator.mul, q, r["vec"])), r))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"id": r["id"], "doc": r["doc"], "title": r.get("title"), "text": r["text"],
                 "score": round(s, 4), "source_uri": r.get("source_uri") or None} for s, r in scored[:limit]]


def passage_search(idx, lake=None) -> "KnowledgeBaseSearch | LocalVectorSearch | KeywordSearch | None":
    """The configured PassageSearch: the Knowledge Base when KNOWLEDGE_BASE_ID is set, else the
    lake's own vectors when embed has written them, else keyword search over the projection, else
    none (no projection yet)."""
    if knowledge_base_id():
        return KnowledgeBaseSearch()
    if has_vectors(lake):
        return LocalVectorSearch(lake)
    return KeywordSearch(idx) if idx is not None else None


def search(lake, idx, cid: str, query: str, *, private: bool, limit: int = 6) -> dict:
    found = passage_search(idx, lake)
    if found is None:
        return {"error": f"collection {cid!r} has no knowledge graph yet"}
    return {"passages": found.search(cid, query, private=private, limit=limit), "method": found.method}
