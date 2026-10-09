"""The portal's projection in a document store, for collections too large to hold in memory.

    PROJECTION_STORE   memory (the default) | mongodb   (MONGODB_URI, MONGODB_DB as for chat state)

The pipeline's load stage copies the index files project() writes into three collections
(entities, passages, docs), each document tagged with `g`: the collection, version and build it
belongs to. As with the graph, a load is checked by count before the lake's pointer
(layout.DOCUMENTS_POINTER) moves to it, the previous load is kept and older ones are dropped.

DocIndex serves the same methods as the in-memory Index and gives the same answers, reading only
what a request needs. Search uses token arrays with multikey indexes, not $text or Atlas Search,
so it runs on MongoDB and services compatible with it alike.
"""

from __future__ import annotations

import json
import logging
import math
import re
from collections import Counter

from .. import layout
from ..graph import traverse
from .index import Index, tokens

log = logging.getLogger("docstore")

BATCH = 1000
CANDIDATES = 5000   # documents read to rank one search; a search matching more is ranked among these
CACHE = 5000        # documents a DocIndex keeps between requests


def connect(uri: str, db: str):
    from pymongo import MongoClient
    return MongoClient(uri, retryWrites=False, serverSelectionTimeoutMS=10000)[db]


def ensure_indexes(db) -> None:
    from pymongo import ASCENDING, DESCENDING
    db.entities.create_index([("g", ASCENDING), ("types", ASCENDING)])
    db.entities.create_index([("g", ASCENDING), ("tokens", ASCENDING)])
    db.entities.create_index([("g", ASCENDING), ("rank", DESCENDING), ("label_lc", ASCENDING)])
    db.entities.create_index([("g", ASCENDING), ("links", DESCENDING), ("label_lc", ASCENDING)])
    db.passages.create_index([("g", ASCENDING), ("tokens", ASCENDING)])


def key_for(collection: str, version: str, built_at: str) -> str:
    return f"{collection}@{version}@{re.sub(r'[^0-9]', '', built_at)[:14]}"


def _names(e: dict) -> str:
    return " ".join([e["label"], *e["aliases"]]).lower()


def load(db, key: str, entities: list[dict], passages: dict, docs: dict) -> dict:
    """Write one projection under `key`; return what was counted back."""
    ensure_indexes(db)
    drop(db, key)
    rows = {
        "entities": [{**e, "_id": f"{key}|{e['id']}", "g": key, "tokens": sorted(set(tokens(_names(e)))),
                      "label_lc": e["label"].lower(), "rank": len(e["docs"]) + len(e["out"]) + len(e["in"]),
                      "links": len(e["out"]) + len(e["in"])}
                     for e in entities],
        "passages": [{**p, "_id": f"{key}|{pid}", "id": pid, "g": key, "tokens": sorted(set(tokens(p["text"])))}
                     for pid, p in passages.items()],
        "docs": [{**d, "_id": f"{key}|{did}", "id": did, "g": key} for did, d in docs.items()],
    }
    for name, docs_ in rows.items():
        for i in range(0, len(docs_), BATCH):
            db[name].insert_many(docs_[i:i + BATCH], ordered=False)
    return {name: db[name].count_documents({"g": key}) for name in rows}


def drop(db, key: str) -> None:
    for name in ("entities", "passages", "docs"):
        db[name].delete_many({"g": key})


def keys(db, collection: str) -> list[str]:
    return sorted(db.entities.distinct("g", {"g": {"$regex": f"^{re.escape(collection)}@"}}))


def _plain(doc: dict | None) -> dict | None:
    if doc is None:
        return None
    return {k: v for k, v in doc.items() if k not in ("_id", "g", "tokens", "label_lc", "rank", "links")}


class _Lookup:
    """A read-through mapping over one collection for one load: what the Index's callers use
    (get, [], in), fetched by id, a batch at a time where the caller knows the ids."""

    def __init__(self, coll, key: str):
        self.coll, self.key, self.cache = coll, key, {}

    def fetch(self, ids) -> None:
        want = [i for i in dict.fromkeys(ids) if i not in self.cache]
        if not want:
            return
        if len(self.cache) + len(want) > CACHE:
            self.cache.clear()
        found = {d["_id"].split("|", 1)[1]: _plain(d)
                 for d in self.coll.find({"_id": {"$in": [f"{self.key}|{i}" for i in want]}})}
        for i in want:
            self.cache[i] = found.get(i)

    def get(self, i, default=None):
        self.fetch([i])
        v = self.cache.get(i)
        return default if v is None else v

    def __getitem__(self, i):
        v = self.get(i)
        if v is None:
            raise KeyError(i)
        return v

    def __contains__(self, i):
        return self.get(i) is not None

    def __len__(self):
        return self.coll.count_documents({"g": self.key})

    def __iter__(self):
        for d in self.coll.find({"g": self.key}, {"_id": 1}):
            yield d["_id"].split("|", 1)[1]


class _Adjacency(traverse.MemoryAdjacency):
    """The in-memory primitives, with each layer's entities and neighbours fetched in two queries."""

    def adjacent(self, ids, private):
        ents = self.idx.entities
        ents.fetch(ids)
        near = [r["o"] for i in ids if ents.get(i) for r in ents.get(i)["out"]] + \
               [r["s"] for i in ids if ents.get(i) for r in ents.get(i)["in"]]
        ents.fetch(near)
        self.idx.passages.fetch(p for i in ids if ents.get(i) for r in ents.get(i)["out"] + ents.get(i)["in"]
                                for p in r["passages"])
        return super().adjacent(ids, private)


class DocIndex(Index):
    def __init__(self, lake, version: str, db, key: str):  # noqa: super().__init__ loads memory; this must not
        get = lambda name: json.loads(lake.get(layout.index_key(version, name)))  # noqa: E731
        self.version, self.key, self.db = version, key, db
        self.summary = get("summary")
        self.ontology = get("ontology")
        self.entities = _Lookup(db.entities, key)
        self.passages = _Lookup(db.passages, key)
        self.docs = _Lookup(db.docs, key)
        self.adjacency = _Adjacency(self)

    def entity_view(self, e, private):
        self.passages.fetch(p for rows in (e["attributes"], e["out"], e["in"]) for r in rows for p in r["passages"])
        self.passages.fetch(e["passages"])
        self.docs.fetch(e["docs"])
        return super().entity_view(e, private)

    def subtree(self, type_):
        return [d["id"] for d in self.db.entities.find({"g": self.key, "types": type_}, {"id": 1})]

    def search_entities(self, q="", type_=None, *, private, limit=25, offset=0):
        flt: dict = {"g": self.key}
        if type_:
            flt["types"] = type_
        if not private:
            flt["scope"] = "public"
        qt = set(tokens(q))
        if not qt:
            total = self.db.entities.count_documents(flt)
            page = self.db.entities.find(flt).sort([("rank", -1), ("label_lc", 1), ("_id", 1)]).skip(offset).limit(limit)
            return {"total": total, "items": [self.brief(_plain(e)) for e in page]}
        match = [{"tokens": {"$in": sorted(qt)}}, {"label_lc": {"$regex": re.escape(q.lower())}},
                 {"aliases": {"$regex": re.escape(q), "$options": "i"}}]
        scored = []
        for e in self.db.entities.find({**flt, "$or": match}).limit(CANDIDATES):
            names = _names(e)
            hit = len(qt & set(tokens(names)))
            if not hit and q.lower() not in names:
                continue
            scored.append((hit + (2 if q.lower() == e["label"].lower() else 0), e["label"].lower(), e["id"], e))
        scored.sort(key=lambda x: (-x[0], x[1], x[2]))
        return {"total": len(scored), "items": [self.brief(_plain(e)) for *_, e in scored[offset:offset + limit]]}

    def search_passages(self, q, *, private, limit=6):
        qt = tokens(q)
        if not qt:
            return []
        n = max(1, self.db.passages.count_documents({"g": self.key}))
        cands = list(self.db.passages.find({"g": self.key, "tokens": {"$in": sorted(set(qt))}}).limit(CANDIDATES))
        df = Counter(t for p in cands for t in set(p["tokens"]))
        scored = []
        for p in cands:
            if not self.visible(p, private):
                continue
            c = Counter(tokens(p["text"]))
            s = sum(c[t] * math.log(1 + n / (1 + df[t])) for t in qt if t in c)
            if s:
                scored.append((s, p["id"]))
                self.passages.cache[p["id"]] = _plain(p)
        scored.sort(reverse=True)
        top = [pid for _, pid in scored[:limit]]
        self.docs.fetch(self.passages[p]["doc"] for p in top)
        return [self.passage_view(pid) for pid in top]

    def graph(self, type_, *, private, limit=150, focus=None):
        if focus:
            e = self.entities.get(focus)
            if e:
                self.entities.fetch([r["o"] for r in e["out"]] + [r["s"] for r in e["in"]])
            return super().graph(type_, private=private, limit=limit, focus=focus)
        flt: dict = {"g": self.key}
        if type_:
            flt["types"] = type_
        if not private:
            flt["scope"] = "public"
        order = [("links", -1), ("label_lc", 1), ("_id", 1)]
        top = [_plain(e) for e in self.db.entities.find(flt).sort(order).limit(limit)]
        for e in top:
            self.entities.cache[e["id"]] = e
        ks = {e["id"] for e in top}
        edges = [{"s": e["id"], "o": r["o"], "p": r["p"]} for e in top
                 for r in self.entity_view(e, private)["out"] if r["o"] in ks]
        return {"nodes": [self.brief(e) for e in top], "edges": edges}
