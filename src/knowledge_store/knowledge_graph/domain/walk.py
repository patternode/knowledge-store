"""The walk: an association graph over phrases and passages, and the spread of a question over it.

Pure. The graph has two kinds of node: a phrase (the subject or object of an open fact, keyed by its
normalised text) and a passage. A fact joins its two phrases; a passage is joined to every phrase
read from it; a synonym edge joins two phrases whose embeddings are close. Spreading is
Personalized PageRank from the phrases a question names, with every passage lightly seeded by its
own similarity to the question, so that the passages best connected to the question's entities
rank first, whether or not they share its words (the HippoRAG 2 design). The walk slice builds the
graph from the lake and runs this over it.
"""

from __future__ import annotations

import re
from collections import defaultdict

PHRASE = "e:"
PASSAGE = "p:"
DAMPING = 0.5          # how far activation spreads: HippoRAG 2's value, two or three hops matter, more is noise
ITERATIONS = 40
TOLERANCE = 1e-7


def phrase_key(text: str) -> str:
    """One key for a phrase however it was written: case, punctuation and spacing folded."""
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def build_graph(facts: list[dict], synonyms: list[tuple[str, str, float]] = (),
                *, ungrounded_weight: float = 0.5) -> dict:
    """The graph as node lists and an adjacency of weights: phrases (key -> a display text),
    passages (id -> doc) and edges. A fact's edge weighs 1, or ungrounded_weight when its subject
    or object was not found in its passage; a passage's edge to a phrase weighs 1; a synonym edge
    weighs its similarity. Weights add up over repeated pairs."""
    phrases: dict[str, str] = {}
    passages: dict[str, str] = {}
    adj: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    def join(a: str, b: str, w: float) -> None:
        if a != b and w > 0:
            adj[a][b] += w
            adj[b][a] += w

    for f in facts:
        s, o, pid = phrase_key(f.get("s", "")), phrase_key(f.get("o", "")), f.get("pid") or ""
        if not s or not o or not pid:
            continue
        phrases.setdefault(s, f["s"])
        phrases.setdefault(o, f["o"])
        passages.setdefault(pid, f.get("doc") or "")
        w = 1.0 if f.get("grounded", True) else ungrounded_weight
        join(PHRASE + s, PHRASE + o, w)
        join(PASSAGE + pid, PHRASE + s, 1.0)
        join(PASSAGE + pid, PHRASE + o, 1.0)
    for a, b, sim in synonyms:
        ka, kb = phrase_key(a), phrase_key(b)
        if ka in phrases and kb in phrases:
            join(PHRASE + ka, PHRASE + kb, float(sim))
    return {"phrases": phrases, "passages": passages,
            "edges": {a: dict(bs) for a, bs in adj.items()}}


def personalized_pagerank(edges: dict[str, dict[str, float]], seeds: dict[str, float], *,
                          damping: float = DAMPING, iterations: int = ITERATIONS, tolerance: float = TOLERANCE) -> dict[str, float]:
    """Scores of every node reachable from the seeds. seeds maps node -> reset weight; the walk
    returns to a seed with probability 1 - damping at each step, so damping sets its reach."""
    total = sum(w for w in seeds.values() if w > 0)
    if total <= 0:
        return {}
    reset = {n: w / total for n, w in seeds.items() if w > 0}
    degree = {n: sum(bs.values()) for n, bs in edges.items()}
    scores = dict(reset)
    for _ in range(iterations):
        spread: dict[str, float] = defaultdict(float)
        for n, s in scores.items():
            d = degree.get(n, 0.0)
            if d <= 0:
                continue   # a node without edges hands its mass back to the seeds below
            share = damping * s / d
            for m, w in edges[n].items():
                spread[m] += share * w
        lost = 1.0 - sum(spread.values())    # what dangling nodes and the reset return to the seeds
        nxt = {n: spread.get(n, 0.0) + lost * r for n, r in reset.items()}
        for n, v in spread.items():
            if n not in reset:
                nxt[n] = v
        delta = sum(abs(nxt.get(n, 0.0) - scores.get(n, 0.0)) for n in set(nxt) | set(scores))
        scores = nxt
        if delta < tolerance:
            break
    return scores


def seeds_from(fact_hits: list[tuple[dict, float]], passage_hits: list[tuple[str, float]], *,
               passage_weight: float = 0.05, top_phrases: int = 5) -> dict[str, float]:
    """The reset weights: each phrase of a retrieved fact by the mean score of the facts it is in,
    the best top_phrases of them, and every passage by its own similarity times passage_weight."""
    by_phrase: dict[str, list[float]] = defaultdict(list)
    for f, score in fact_hits:
        for text in (f.get("s", ""), f.get("o", "")):
            k = phrase_key(text)
            if k:
                by_phrase[k].append(score)
    ranked = sorted(((sum(v) / len(v), k) for k, v in by_phrase.items()), reverse=True)[:top_phrases]
    seeds = {PHRASE + k: max(score, 0.0) for score, k in ranked}
    for pid, score in passage_hits:
        if score > 0:
            seeds[PASSAGE + pid] = seeds.get(PASSAGE + pid, 0.0) + score * passage_weight
    return seeds


def rank_passages(scores: dict[str, float], *, allowed=None, limit: int = 8) -> list[tuple[str, float]]:
    """The best passages by walk score, allowed ids only when given."""
    out = [(n[len(PASSAGE):], s) for n, s in scores.items() if n.startswith(PASSAGE) and s > 0]
    if allowed is not None:
        out = [(pid, s) for pid, s in out if pid in allowed]
    out.sort(key=lambda x: (-x[1], x[0]))
    return out[:limit]
