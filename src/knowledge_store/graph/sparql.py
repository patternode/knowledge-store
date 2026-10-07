"""The knowledge graph in a SPARQL store: Amazon Neptune on AWS.

The gold N-Quads are the record, and a SPARQL store can hold them as they are: one named graph
per document at each version in the active chain, and the active ontology (the T-Box) in a named
graph of its own. pipeline/load.py keeps the store in step with the lake. Neptune's default graph
is the union of its named graphs, so a query sees the active chain and its ontology, and nothing
else of this collection once the loader has dropped what left the chain.

SparqlIndex answers the index's entity queries (portal_api/index.py) from the store:

    search_entities, list_entities   labels and synonyms, typed through rdfs:subClassOf* in the
                                     ontology graph, so a query for a class finds its subclasses
    get_entity                       the entity's types, names, and every reified fact about it
                                     with the passages it was extracted from
    neighbourhood, find_paths        traverse.py over node() and adjacent(), each a few queries

The passages' text is not in the graph (it is in the lake's silver layer); a passage is a node
with its document and the document's scope, which is what scope filtering needs.

Every query text is built from the ontology's own names and from ids checked against a strict
pattern (iri() and lit() below): nothing a caller sends reaches a query unescaped, and there is
no free-form query tool. The tools' IAM policy allows reads only (neptune-db:ReadDataViaQuery).

Standard library and botocore only, so the tools Lambda needs no extra package.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.parse
import urllib.request

from .. import layout
from . import traverse

KS = "https://w3id.org/knowledge-store/core#"
PREFIXES = f"""PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX ks: <{KS}>
"""
BATCH = 200          # ids per VALUES block
CANDIDATES = 500     # entities a search considers before scoring
CACHE_S = 60

_IRI_BAD = re.compile(r"[\s<>\"{}|^`\\]")
_ID = re.compile(r"^[A-Za-z0-9._~%/-]{1,400}$")


class SparqlError(RuntimeError):
    pass


def iri(value: str) -> str:
    if not value or _IRI_BAD.search(value):
        raise ValueError(f"not a safe IRI: {value!r}")
    return f"<{value}>"


def lit(value: str) -> str:
    s = str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")
    return f'"{s}"'


def local_name(value: str) -> str:
    return re.split(r"[#/]", value)[-1]


# --- clients ------------------------------------------------------------------------------------

class NeptuneClient:
    """SPARQL over HTTPS to a Neptune cluster, signed with SigV4 when IAM authentication is on."""

    def __init__(self, endpoint: str, port: int = 8182, region: str | None = None, iam: bool = True,
                 timeout: int = 60):
        self.url = f"https://{endpoint}:{port}/sparql"
        self.region = region or os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
        self.iam, self.timeout = iam, timeout

    @classmethod
    def from_env(cls) -> "NeptuneClient | None":
        host = os.environ.get("NEPTUNE_ENDPOINT")
        if not host:
            return None
        return cls(host, int(os.environ.get("NEPTUNE_PORT", "8182")),
                   iam=os.environ.get("NEPTUNE_IAM_AUTH", "true") != "false")

    def _post(self, form: dict, accept: str) -> bytes:
        body = urllib.parse.urlencode(form).encode()
        headers = {"Content-Type": "application/x-www-form-urlencoded", "Accept": accept}
        if self.iam:
            import boto3
            from botocore.auth import SigV4Auth
            from botocore.awsrequest import AWSRequest
            req = AWSRequest(method="POST", url=self.url, data=body, headers=headers)
            SigV4Auth(boto3.Session().get_credentials().get_frozen_credentials(), "neptune-db", self.region).add_auth(req)
            headers = dict(req.headers)
        r = urllib.request.Request(self.url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(r, timeout=self.timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            raise SparqlError(f"Neptune {e.code}: {e.read()[:500].decode(errors='replace')}") from e

    def select(self, query: str) -> list[dict[str, tuple[str, str]]]:
        out = json.loads(self._post({"query": PREFIXES + query}, "application/sparql-results+json"))
        return [{k: (v["type"], v["value"]) for k, v in b.items()} for b in out["results"]["bindings"]]

    def update(self, update: str) -> None:
        self._post({"update": PREFIXES + update}, "application/json")


class LocalClient:
    """The same two calls over an in-memory rdflib dataset whose default graph is the union of
    its named graphs, as Neptune's is: for tests and local runs without a SPARQL server."""

    def __init__(self):
        from rdflib import Dataset
        self.ds = Dataset(default_union=True)

    def select(self, query: str) -> list[dict[str, tuple[str, str]]]:
        from rdflib import BNode, Literal
        res = self.ds.query(PREFIXES + query)
        rows = []
        for row in res:
            d = {}
            for var in res.vars:
                val = row[var]
                if val is not None:
                    kind = "literal" if isinstance(val, Literal) else "bnode" if isinstance(val, BNode) else "uri"
                    d[str(var)] = (kind, str(val))
            rows.append(d)
        return rows

    def update(self, update: str) -> None:
        self.ds.update(PREFIXES + update)


def client_from_env():
    return NeptuneClient.from_env()


def value(row: dict, name: str, default: str = "") -> str:
    return row[name][1] if name in row else default


def chunks(items: list, n: int = BATCH):
    for i in range(0, len(items), n):
        yield items[i:i + n]


# --- the index over the store -------------------------------------------------------------------

class _Lookup:
    """A read-through mapping (get, [], in) that fetches a batch of ids at a time."""

    def __init__(self, fetch):
        self._fetch, self.cache = fetch, {}

    def fetch(self, ids) -> None:
        want = [i for i in dict.fromkeys(ids) if i and i not in self.cache]
        if want:
            if len(self.cache) > 20000:
                self.cache.clear()
            found = self._fetch(want)
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


class _Adjacency(traverse.MemoryAdjacency):
    """The in-memory primitives, with each layer's entities, neighbours and passages fetched in
    batches rather than one query per node."""

    def adjacent(self, ids, private):
        ents = self.idx.entities
        ents.fetch(ids)
        near = [r["o"] for i in ids if ents.get(i) for r in ents.get(i)["out"]] + \
               [r["s"] for i in ids if ents.get(i) for r in ents.get(i)["in"]]
        ents.fetch(near)
        return super().adjacent(ids, private)


class SparqlIndex:
    """What the tools ask of an index, answered from the knowledge graph. The profile, the
    ontology's terms and the documents' titles come from the lake's projection of the same build."""

    def __init__(self, lake, version: str, client):
        from ..portal_api.index import Index
        get = lambda name: json.loads(lake.get(layout.index_key(version, name)))  # noqa: E731
        self._Index = Index
        self.version, self.client = version, client
        self.summary = get("summary")
        self.ontology = get("ontology")
        self.docs = get("docs")
        self.ns = self.ontology["namespace"]
        self.base = self.ns.rstrip("#/") + "/id/"
        self.classes = {c["name"]: c for c in self.ontology["classes"]}
        self.class_iri = {c["name"]: c.get("iri") or self.ns + c["name"] for c in self.ontology["classes"]}
        self.passages = _Lookup(self._fetch_passages)
        self.entities = _Lookup(self._fetch_entities)
        self.adjacency = _Adjacency(self)

    # the parts of Index that need nothing but entities, passages and docs
    visible = staticmethod(lambda item, private: private or item.get("scope", "public") == "public")

    def entity_view(self, e: dict, private: bool) -> dict:
        self.entities.fetch([r["o"] for r in e["out"]] + [r["s"] for r in e["in"]])
        return self._Index.entity_view(self, e, private)

    def brief(self, e: dict) -> dict:
        return self._Index.brief(self, e)

    def summary_view(self, private: bool) -> dict:
        return self._Index.summary_view(self, private)

    def neighbourhood(self, focus: str, *, hops: int = 1, private: bool, limit: int = 40) -> dict:
        return traverse.neighbourhood(self.adjacency, focus, hops=hops, private=private, limit=limit)

    def paths(self, source: str, target: str, *, max_hops: int = 3, private: bool, limit: int = 10) -> dict:
        return traverse.paths(self.adjacency, source, target, max_hops=max_hops, private=private, limit=limit)

    def passage_view(self, pid: str) -> dict:
        p = self.passages[pid]
        d = self.docs.get(p["doc"], {})
        return {"id": pid, "doc": p["doc"], "title": d.get("title") or d.get("name")}

    def search_passages(self, q: str, *, private: bool, limit: int = 6) -> list[dict]:
        raise NotImplementedError("passage text is not in the graph; search_passages is a passage tool")

    # -- ontology --------------------------------------------------------------------------------

    def ancestors(self, name: str) -> set[str]:
        seen, todo = set(), [name]
        while todo:
            n = todo.pop()
            if n not in seen and n in self.classes:
                seen.add(n)
                todo += self.classes[n].get("parents") or []
        return seen

    def _short(self, value: str, kind: str) -> str:
        pre = self.base + (kind + "/" if kind else "")
        return value[len(pre):] if value.startswith(pre) else value

    # -- fetches ---------------------------------------------------------------------------------

    def _fetch_passages(self, ids: list[str]) -> dict[str, dict]:
        out = {}
        safe = [i for i in ids if _ID.match(i)]
        for part in chunks(safe):
            vals = " ".join(iri(self.base + "passage/" + i) for i in part)
            for r in self.client.select(f"SELECT ?p ?d ?scope WHERE {{ VALUES ?p {{ {vals} }} "
                                        f"?p ks:partOf ?d . OPTIONAL {{ ?d ks:scope ?scope }} }}"):
                out[self._short(value(r, "p"), "passage")] = {"doc": self._short(value(r, "d"), "doc"),
                                                              "scope": value(r, "scope", "public")}
        return out

    def _fetch_entities(self, ids: list[str]) -> dict[str, dict]:
        safe = [i for i in ids if _ID.match(i) and i.startswith("entity/")]
        nodes: dict[str, dict] = {}
        facts: dict[tuple, set] = {}
        for part in chunks(safe):
            vals = " ".join(iri(self.base + i) for i in part)
            for r in self.client.select(
                    f"SELECT ?e ?k ?v WHERE {{ VALUES ?e {{ {vals} }} "
                    f"{{ ?e a ?v . BIND(\"t\" AS ?k) }} UNION {{ ?e rdfs:label ?v . BIND(\"l\" AS ?k) }} UNION "
                    f"{{ ?e skos:altLabel ?v . BIND(\"a\" AS ?k) }} UNION {{ ?e ks:mentionedIn ?v . BIND(\"m\" AS ?k) }} }}"):
                n = nodes.setdefault(self._short(value(r, "e"), ""), {"t": set(), "l": [], "a": set(), "m": set()})
                k, v = value(r, "k"), value(r, "v")
                (n[k].append(v) if k == "l" else n[k].add(v))
            for r in self.client.select(
                    f"SELECT ?s ?p ?o ?src WHERE {{ VALUES ?x {{ {vals} }} "
                    f"{{ ?a rdf:subject ?x }} UNION {{ ?a rdf:object ?x }} "
                    f"?a rdf:subject ?s ; rdf:predicate ?p ; rdf:object ?o . OPTIONAL {{ ?a ks:extractedFrom ?src }} }}"):
                kind, o = r["o"]
                key = (value(r, "s"), value(r, "p"), kind, o)
                srcs = facts.setdefault(key, set())
                if "src" in r:
                    srcs.add(self._short(value(r, "src"), "passage"))
        pids = {self._short(m, "passage") for n in nodes.values() for m in n["m"]} | {p for s in facts.values() for p in s}
        self.passages.fetch(sorted(pids))
        out = {}
        for eid, n in nodes.items():
            types = sorted({local_name(t) for t in n["t"] if t.startswith(self.ns) and local_name(t) in self.classes})
            if not types:
                continue
            most = [t for t in types if not any(t != u and t in self.ancestors(u) for u in types)]
            mentioned = sorted(self._short(m, "passage") for m in n["m"])
            docs = sorted({self.passages.get(p, {}).get("doc", "") for p in mentioned} - {""})
            out[eid] = {"id": eid, "type": most[0], "types": types,
                        "label": (sorted(n["l"]) or [eid.rsplit("/", 1)[-1]])[0], "aliases": sorted(n["a"]),
                        "attributes": [], "out": [], "in": [], "passages": mentioned, "docs": docs,
                        "scope": "public" if any(self.docs.get(d, {}).get("scope", "public") == "public" for d in docs)
                        else "private"}
        for (s, p, kind, o), srcs in sorted(facts.items()):
            if not p.startswith(self.ns):
                continue
            sid, prop, cited = self._short(s, ""), local_name(p), sorted(srcs)
            if kind == "literal":
                if sid in out:
                    out[sid]["attributes"].append({"p": prop, "v": o, "passages": cited})
            elif o.startswith(self.base + "entity/"):
                oid = self._short(o, "")
                if sid in out:
                    out[sid]["out"].append({"p": prop, "o": oid, "passages": cited})
                if oid in out:
                    out[oid]["in"].append({"p": prop, "s": sid, "passages": cited})
        return out

    # -- search ----------------------------------------------------------------------------------

    def search_entities(self, q: str = "", type_: str | None = None, *, private: bool, limit: int = 25,
                        offset: int = 0) -> dict:
        from ..portal_api.index import tokens
        if type_ and type_ not in self.classes:
            return {"total": 0, "items": [], "error": f"no type {type_!r} in the ontology; see describe_ontology"}
        typed = f"?e a/rdfs:subClassOf* {iri(self.class_iri[type_])} ." if type_ else ""
        mine = f"FILTER(STRSTARTS(STR(?e), {lit(self.base + 'entity/')}))"
        qt = sorted(set(tokens(q)))
        if qt:
            terms = [f"CONTAINS(LCASE(STR(?n)), {lit(t)})" for t in qt] + [f"CONTAINS(LCASE(STR(?n)), {lit(q.lower())})"]
            rows = self.client.select(
                f"SELECT DISTINCT ?e WHERE {{ {{ ?e rdfs:label ?n }} UNION {{ ?e skos:altLabel ?n }} {mine} "
                f"FILTER({' || '.join(terms)}) {typed} }} LIMIT {CANDIDATES}")
        else:
            rows = self.client.select(
                f"SELECT ?e (COUNT(DISTINCT ?a) AS ?n) WHERE {{ ?e ks:mentionedIn ?m . {mine} {typed} "
                f"OPTIONAL {{ {{ ?a rdf:subject ?e }} UNION {{ ?a rdf:object ?e }} }} }} "
                f"GROUP BY ?e ORDER BY DESC(?n) LIMIT {CANDIDATES}")
        ids = [self._short(value(r, "e"), "") for r in rows]
        self.entities.fetch(ids)
        scored = []
        for i in dict.fromkeys(ids):
            e = self.entities.get(i)
            if not e or not self.visible(e, private):
                continue
            if qt:
                names = " ".join([e["label"], *e["aliases"]]).lower()
                hit = len(set(qt) & set(tokens(names)))
                if not hit and q.lower() not in names:
                    continue
                score = hit + (2 if q.lower() == e["label"].lower() else 0)
            else:
                score = len(e["docs"]) + len(e["out"]) + len(e["in"])
            scored.append((score, e["label"].lower(), i))
        scored.sort(key=lambda x: (-x[0], x[1], x[2]))
        return {"total": len(scored), "items": [self.brief(self.entities[i]) for _, _, i in scored[offset:offset + limit]]}


_cache: dict[str, dict] = {}


def load(lake, key: str, client) -> SparqlIndex | None:
    """The collection's index over the store, rechecked at most every CACHE_S seconds."""
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
    if idx is None or idx.version != active or idx.summary.get("built_at") != built:
        idx = SparqlIndex(lake, active, client)
    c.update(checked=now, index=idx)
    return idx
