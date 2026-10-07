"""The passage tools' two sources: the Knowledge Base for search, the lake for text.

search   the Bedrock Knowledge Base (vectors in S3 Vectors) when KNOWLEDGE_BASE_ID is set: one
         vector per passage, filtered to the collection and, for a caller outside the private
         scope, to public passages. Without one, keyword search over the projection's passages.
read     the passage's text from the projection, or from the silver layer for a passage no fact
         cites (a search hit can be one). The caller's scope is checked against the document's.

A passage id begins with the first 16 characters of its document's id (refine/chunk.py), which
is how a passage is found in silver without an index.
"""

from __future__ import annotations

import os

from .. import layout

PASSAGE_ID_PREFIX = 16


def knowledge_base_id() -> str | None:
    return os.environ.get("KNOWLEDGE_BASE_ID") or None


def kb_search(cid: str, query: str, *, private: bool, limit: int = 6, client=None) -> list[dict]:
    import boto3
    client = client or boto3.client("bedrock-agent-runtime")
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
    from ..pipeline.refine import load_doc, load_passages
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


def search(lake, idx, cid: str, query: str, *, private: bool, limit: int = 6) -> dict:
    if knowledge_base_id():
        return {"passages": kb_search(cid, query, private=private, limit=limit), "method": "vector"}
    if idx is None:
        return {"error": f"collection {cid!r} has no knowledge graph yet"}
    return {"passages": idx.search_passages(query, private=private, limit=limit), "method": "keyword"}
