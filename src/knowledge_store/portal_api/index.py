"""The projection, loaded from the lake and cached per active version and build time, with
scope filtering and simple search. Private content is visible only to private-scope callers.

Neighbourhoods and paths come from the graph backend when the lake points at a graph loaded
from this very index (see pipeline/load.py), and from memory otherwise; both run the same
traversal (graph/traverse.py), so the answer does not depend on which."""

from __future__ import annotations

import json
import math
import os
import re
import time
from collections import Counter, defaultdict

from .. import graph, layout
from ..graph import traverse

CACHE_S = 60


def tokens(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", s.lower())


class Index:
    def __init__(self, lake, version: str):
        get = lambda name: json.loads(lake.get(layout.index_key(version, name)))  # noqa: E731
        self.version = version
        self.summary = get("summary")
        self.ontology = get("ontology")
        self.entities = {e["id"]: e for e in get("entities")}
        self.passages = get("passages")
        self.docs = get("docs")
        self.adjacency = traverse.MemoryAdjacency(self)
        self._df: Counter = Counter()
        self._ptoks: dict[str, Counter] = {}
        for pid, p in self.passages.items():
            c = Counter(tokens(p["text"]))
            self._ptoks[pid] = c
            self._df.update(c.keys())
        self.by_type: dict[str, list[str]] = defaultdict(list)
        for e in self.entities.values():
            for t in e["types"]:
                self.by_type[t].append(e["id"])

    # -- scope ----------------------------------------------------------------------------

    @staticmethod
    def visible(item: dict, private: bool) -> bool:
        return private or item.get("scope", "public") == "public"

    def entity_view(self, e: dict, private: bool) -> dict:
        def ok(row):
            return any(self.visible(self.passages.get(p, {}), private) for p in row["passages"])
        return {**e, "attributes": [a for a in e["attributes"] if ok(a)], "out": [r for r in e["out"] if ok(r)],
                "in": [r for r in e["in"] if ok(r)],
                "passages": [p for p in e["passages"] if self.visible(self.passages.get(p, {}), private)],
                "docs": [d for d in e["docs"] if self.visible(self.docs.get(d, {}), private)]}

    def summary_view(self, private: bool) -> dict:
        """The summary, with candidate evidence from private documents withheld from callers
        outside the private scope (a term seen only in private documents is withheld entirely)."""
        if private:
            return self.summary
        cands = []
        for t in self.summary.get("candidates") or []:
            ev = [e for e in t.get("evidence") or [] if e.get("scope", "private") == "public"]
            if ev:
                cands.append({**t, "evidence": ev, "docs": len({e["doc_id"] for e in ev}),
                              "definitions": t.get("definitions") if t.get("scope") == "public" else []})
        return {**self.summary, "candidates": cands}

    # -- queries --------------------------------------------------------------------------

    def search_entities(self, q: str = "", type_: str | None = None, *, private: bool, limit: int = 25,
                        offset: int = 0) -> dict:
        ids = self.subtree(type_) if type_ else list(self.entities)
        qt = set(tokens(q))
        scored = []
        for i in ids:
            e = self.entities[i]
            if not self.visible(e, private):
                continue
            if qt:
                names = " ".join([e["label"], *e["aliases"]]).lower()
                nt = set(tokens(names))
                hit = len(qt & nt)
                if not hit and q.lower() not in names:
                    continue
                score = hit + (2 if q.lower() == e["label"].lower() else 0)
            else:
                score = len(e["docs"]) + len(e["out"]) + len(e["in"])
            scored.append((score, e["label"].lower(), i))
        scored.sort(key=lambda x: (-x[0], x[1], x[2]))
        page = scored[offset:offset + limit]
        return {"total": len(scored), "items": [self.brief(self.entities[i]) for _, _, i in page]}

    def subtree(self, type_: str) -> list[str]:
        return list(dict.fromkeys(self.by_type.get(type_, [])))

    def brief(self, e: dict) -> dict:
        return {"id": e["id"], "label": e["label"], "type": e["type"], "aliases": e["aliases"][:5],
                "docs": len(e["docs"]), "links": len(e["out"]) + len(e["in"])}

    def search_passages(self, q: str, *, private: bool, limit: int = 6) -> list[dict]:
        qt = tokens(q)
        n = max(1, len(self.passages))
        scored = []
        for pid, c in self._ptoks.items():
            p = self.passages[pid]
            if not self.visible(p, private):
                continue
            s = sum(c[t] * math.log(1 + n / (1 + self._df[t])) for t in qt if t in c)
            if s:
                scored.append((s, pid))
        scored.sort(reverse=True)
        return [self.passage_view(pid) for _, pid in scored[:limit]]

    def passage_view(self, pid: str) -> dict:
        p = self.passages[pid]
        d = self.docs.get(p["doc"], {})
        return {"id": pid, "doc": p["doc"], "title": d.get("title") or d.get("name"), "text": p["text"], "seq": p["seq"],
                "format": d.get("format", "text")}

    def graph(self, type_: str | None, *, private: bool, limit: int = 150, focus: str | None = None) -> dict:
        """Nodes and edges for the graph view: the best-connected entities (of a type, or
        around a focus entity), and the relations among them."""
        if focus and focus in self.entities:
            e = self.entities[focus]
            ids = [focus] + [r["o"] for r in e["out"]] + [r["s"] for r in e["in"]]
        else:
            ids = self.subtree(type_) if type_ else list(self.entities)
            ids.sort(key=lambda i: (-(len(self.entities[i]["out"]) + len(self.entities[i]["in"])),
                                    self.entities[i]["label"].lower(), i))
        keep = [i for i in dict.fromkeys(ids) if i in self.entities and self.visible(self.entities[i], private)][:limit]
        ks = set(keep)
        edges = []
        for i in keep:
            for r in self.entity_view(self.entities[i], private)["out"]:
                if r["o"] in ks:
                    edges.append({"s": i, "o": r["o"], "p": r["p"]})
        return {"nodes": [self.brief(self.entities[i]) for i in keep], "edges": edges}


    def neighbourhood(self, focus: str, *, hops: int = 1, private: bool, limit: int = 40) -> dict:
        return traverse.neighbourhood(self.adjacency, focus, hops=hops, private=private, limit=limit)

    def paths(self, source: str, target: str, *, max_hops: int = 3, private: bool, limit: int = 10) -> dict:
        return traverse.paths(self.adjacency, source, target, max_hops=max_hops, private=private, limit=limit)


_cache: dict[str, dict] = {}


def _attach_graph(lake, idx: Index) -> None:
    """Point the index's traversals at the graph backend if the lake's graph was loaded from this
    index, and back at memory if not."""
    store = graph.store()
    ptr = json.loads(lake.get(layout.GRAPH_POINTER)) if store and lake.exists(layout.GRAPH_POINTER) else {}
    loaded = (ptr.get("backend"), ptr.get("version"), ptr.get("built_at"))
    if store and loaded == (store.name, idx.version, idx.summary.get("built_at")):
        if getattr(idx, "graph_key", None) != ptr["key"]:
            idx.adjacency, idx.graph_key = store.bind(ptr["key"]), ptr["key"]
    elif getattr(idx, "graph_key", None):
        idx.adjacency, idx.graph_key = traverse.MemoryAdjacency(idx), None


def _documents(lake, version: str, built: str):
    """The document store's load of this index, if PROJECTION_STORE=mongodb and the lake points
    at one: (db, key), else None."""
    if os.environ.get("PROJECTION_STORE", "memory") != "mongodb" or not lake.exists(layout.DOCUMENTS_POINTER):
        return None
    ptr = json.loads(lake.get(layout.DOCUMENTS_POINTER))
    if (ptr.get("version"), ptr.get("built_at")) != (version, built):
        return None
    if "db" not in _db:
        from .docstore import connect
        _db["db"] = connect(os.environ["MONGODB_URI"], os.environ.get("MONGODB_DB", "knowledge_store"))
    return _db["db"], ptr["key"]


_db: dict = {}


def load(lake, key: str = "") -> Index | None:
    """The collection's index, rechecked at most every CACHE_S seconds (key names the collection).
    From the document store when one holds this build (docstore.py), else from the lake into memory."""
    now = time.time()
    c = _cache.setdefault(key, {})
    if c.get("checked", 0) > now - CACHE_S and "index" in c:
        return c["index"]
    active = json.loads(lake.get(layout.ONTOLOGY_ACTIVE))["version"] if lake.exists(layout.ONTOLOGY_ACTIVE) else None
    if not active or not lake.exists(layout.index_key(active, "summary")):
        c.update(checked=now, index=None)
        return None
    built = json.loads(lake.get(layout.index_key(active, "summary")))["built_at"]
    idx = c.get("index")
    docs = _documents(lake, active, built)
    stale = idx is None or idx.version != active or idx.summary.get("built_at") != built
    if stale or getattr(idx, "key", None) != (docs[1] if docs else None):
        if docs:
            from .docstore import DocIndex
            idx = DocIndex(lake, active, *docs)
        else:
            idx = Index(lake, active)
    _attach_graph(lake, idx)
    c.update(checked=now, index=idx)
    return idx
