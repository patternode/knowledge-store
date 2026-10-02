"""Neighbourhoods and paths, computed from two primitives any graph can answer (Adjacency: a
node by id, and the relations of a set of nodes). The in-memory index and every backend run this
same code, so they give the same answers; a backend only makes the primitives fast.

Both walk breadth first, a layer per call to adjacent(), and see only what the caller may: a
public caller never passes through a private node or along a private relation, so a public
entity reachable only through private text is not reachable at all.
"""

from __future__ import annotations

from collections import defaultdict

MAX_HOPS = 4
MAX_NEIGHBOURHOOD_HOPS = 3
MAX_VISITED = 20000
MAX_ENUMERATED = 1000


def visible(item: dict, private: bool) -> bool:
    return private or item.get("scope", "public") == "public"


def brief(n: dict) -> dict:
    """The shape the index's brief() gives an entity."""
    return {"id": n["id"], "label": n["name"], "type": n["type"], "aliases": list(n.get("aliases") or [])[:5],
            "docs": n.get("docs", 0), "links": n.get("links", 0)}


def _steps(adj, frontier: list[str], private: bool):
    """(edge, neighbour, the frontier node it was reached from), visible to the caller."""
    for edge, n in adj.adjacent(frontier, private):
        if not (visible(edge, private) and visible(n, private)):
            continue
        if edge["s"] == edge["o"]:
            continue
        yield edge, n, (edge["o"] if edge["s"] == n["id"] else edge["s"])


def neighbourhood(adj, focus: str, *, hops: int = 1, private: bool, limit: int = 40) -> dict:
    """The entities within `hops` relations of one entity, nearest and best connected first,
    and the relations among them."""
    hops = max(1, min(int(hops), MAX_NEIGHBOURHOOD_HOPS))
    limit = max(1, min(int(limit), 200))
    start = adj.node(focus)
    if not start or not visible(start, private):
        return {"nodes": [], "edges": [], "hops": hops}
    dist: dict[str, tuple[int, dict]] = {focus: (0, start)}
    frontier = [focus]
    for d in range(1, hops + 1):
        if len(dist) >= limit or not frontier:
            break
        nxt = []
        for _, n, _ in _steps(adj, frontier, private):
            if n["id"] not in dist:
                dist[n["id"]] = (d, n)
                nxt.append(n["id"])
        frontier = nxt
    keep = sorted(dist.items(), key=lambda kv: (kv[1][0], -kv[1][1].get("links", 0), kv[1][1]["name"].lower(), kv[0]))
    keep = keep[:limit]
    ks = {k for k, _ in keep}
    edges = {(e["s"], e["p"], e["o"]) for e, _, _ in _steps(adj, sorted(ks), private) if e["s"] in ks and e["o"] in ks}
    return {"nodes": [brief(n) for _, (_, n) in keep],
            "edges": [{"s": s, "o": o, "p": p} for s, p, o in sorted(edges)], "hops": hops}


def paths(adj, source: str, target: str, *, max_hops: int = 3, private: bool, limit: int = 10) -> dict:
    """Every shortest chain of relations from one entity to another, in either direction along
    each relation, up to max_hops long. A chain is its entities and the relations between them,
    each relation in its own direction."""
    max_hops = max(1, min(int(max_hops), MAX_HOPS))
    limit = max(1, min(int(limit), 20))
    a, b = adj.node(source), adj.node(target)
    empty = {"paths": [], "hops": None, "truncated": False}
    if source == target or not a or not b or not (visible(a, private) and visible(b, private)):
        return empty
    dist = {source: 0}
    nodes = {source: a}
    preds: dict[str, set[tuple[str, str, str, str]]] = defaultdict(set)  # node -> {(prev, s, p, o)}
    frontier, truncated = [source], False
    for d in range(1, max_hops + 1):
        nxt: list[str] = []
        for e, n, u in _steps(adj, frontier, private):
            v = n["id"]
            if dist.get(v, d) < d:
                continue
            if v not in dist:
                dist[v] = d
                nodes[v] = n
                nxt.append(v)
            preds[v].add((u, e["s"], e["p"], e["o"]))
        if target in dist:
            break
        if len(dist) > MAX_VISITED:
            truncated = True
            break
        frontier = nxt
        if not frontier:
            break
    if target not in dist:
        return {**empty, "truncated": truncated}

    chains: list[tuple[list[str], list[tuple[str, str, str]]]] = []

    def back(v: str, ids: list[str], rels: list[tuple[str, str, str]]) -> None:
        if len(chains) >= MAX_ENUMERATED:
            return
        if v == source:
            chains.append(([source, *reversed(ids)], list(reversed(rels))))
            return
        for u, s, p, o in sorted(preds[v]):
            back(u, [*ids, v], [*rels, (s, p, o)])

    back(target, [], [])
    chains.sort()
    return {"paths": [{"nodes": [brief(nodes[i]) for i in ids], "edges": [{"s": s, "o": o, "p": p} for s, p, o in rels]}
                      for ids, rels in chains[:limit]],
            "hops": dist[target], "truncated": truncated or len(chains) >= MAX_ENUMERATED}


class MemoryAdjacency:
    """The primitives over the portal's in-memory index."""

    def __init__(self, idx):
        self.idx = idx

    def _scope(self, pids) -> str:
        return "public" if any(self.idx.passages.get(p, {}).get("scope") == "public" for p in pids) else "private"

    def node(self, node_id):
        e = self.idx.entities.get(node_id)
        if not e:
            return None
        return {"id": e["id"], "name": e["label"], "type": e["type"], "aliases": e["aliases"], "docs": len(e["docs"]),
                "links": len(e["out"]) + len(e["in"]), "scope": e.get("scope", "public")}

    def adjacent(self, ids, private):
        out = []
        for i in dict.fromkeys(ids):
            e = self.idx.entities.get(i)
            if not e:
                continue
            for r in e["out"]:
                n = self.node(r["o"])
                if n:
                    out.append(({"s": i, "o": r["o"], "p": r["p"], "scope": self._scope(r["passages"])}, n))
            for r in e["in"]:
                n = self.node(r["s"])
                if n:
                    out.append(({"s": r["s"], "o": i, "p": r["p"], "scope": self._scope(r["passages"])}, n))
        return [(e, n) for e, n in out if private or (e["scope"] == "public" and n["scope"] == "public")]
