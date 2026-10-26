"""Build the walk from the lake, and find the passages most connected to a question.

build_walk reads the open facts (the extraction context's contract) and the passage vectors
(embed), embeds every distinct phrase and every fact, links phrases whose vectors are close as
synonyms, and writes the graph (layout.WALK_GRAPH) and the vectors (layout.WALK_VECTORS). The
embedder is given, as in embed, so this slice holds no SDK.

related answers one question: the question is embedded, the closest facts seed their phrases,
every passage is seeded by its own similarity, Personalized PageRank spreads the activation
(domain/walk.py), and the top passages come back with their text, in the caller's scope, with
the facts that led there. One call finds the second and third passage of a multi-hop question
that a search for the question's words would miss. An optional keep(question, facts) callable,
HippoRAG 2's recognition memory, drops seed facts a small model judges irrelevant.
"""

from __future__ import annotations

import datetime as dt
import json
import operator
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from knowledge_store.extraction import open_fact_rows
from knowledge_store.knowledge_graph.domain import walk as graph
from knowledge_store.knowledge_graph.slices.embed import read_vectors
from knowledge_store.platform_services import layout

BATCH = 16
EMBED_ATTEMPTS = 6         # a batch is retried on any error, with backoff: Titan returns transient model errors
CHECKPOINT_EVERY = 2000    # new embeddings between writes of the vectors file, so a failed build resumes
SYNONYM_THRESHOLD = 0.8
MAX_SYNONYMS = 5           # synonym edges a phrase keeps, its closest
TOP_FACTS = 10             # facts retrieved for the question before seeding
CACHE_S = 60
_cache: dict[tuple, tuple[float, dict]] = {}


def fact_text(f: dict) -> str:
    return f"{f['s']} {f['p']} {f['o']}"


def _embed_batch(embedder, batch: list[str]) -> list[list[float]]:
    for attempt in range(EMBED_ATTEMPTS):
        try:
            return embedder.embed(batch)
        except Exception:
            if attempt == EMBED_ATTEMPTS - 1:
                raise
            time.sleep(min(60, 2 ** attempt))
    raise RuntimeError("unreachable: the last attempt raises")   # pragma: no cover


def _embed_all(embedder, texts: list[str], workers: int, *, known: dict[str, list[float]] | None = None,
               checkpoint=None) -> list[list[float]]:
    """A vector a text. Texts in known keep their vector and are not sent; checkpoint(vectors_so_far),
    when given, is called every CHECKPOINT_EVERY new embeddings so a build that fails resumes."""
    known = known or {}
    out: list[list[float] | None] = [known.get(x) for x in texts]
    todo = [i for i, v in enumerate(out) if v is None]
    lock = threading.Lock()
    done = {"n": 0, "at": 0}

    def run(start: int) -> None:
        idx = todo[start:start + BATCH]
        for i, vec in zip(idx, _embed_batch(embedder, [texts[i] for i in idx])):
            out[i] = [round(x, 6) for x in vec]
        with lock:
            done["n"] += len(idx)
            if checkpoint is not None and done["n"] - done["at"] >= CHECKPOINT_EVERY:
                done["at"] = done["n"]
                checkpoint({texts[i]: v for i, v in enumerate(out) if v is not None})

    with ThreadPoolExecutor(max(1, workers)) as ex:
        list(ex.map(run, range(0, len(todo), BATCH)))
    return [v or [] for v in out]


def _known_vectors(lake, embedder) -> dict[str, list[float]]:
    """Text -> vector from a vectors file an earlier build (or checkpoint) wrote with the same model."""
    if not lake.exists(layout.WALK_VECTORS):
        return {}
    rows = [json.loads(line) for line in lake.get(layout.WALK_VECTORS).decode().splitlines() if line.strip()]
    if not rows or rows[0].get("model") != embedder.model or rows[0].get("dim") != embedder.dimensions:
        return {}
    out = {}
    for r in rows[1:]:
        if r.get("vec"):
            out[fact_text(r) if r.get("kind") == "fact" else r.get("text", "")] = r["vec"]
    return out


def synonym_pairs(keys: list[str], vecs: list[list[float]], *, threshold: float = SYNONYM_THRESHOLD,
                  per_phrase: int = MAX_SYNONYMS) -> list[tuple[str, str, float]]:
    """Phrase pairs whose vectors are at least threshold alike, each phrase's closest per_phrase.
    With numpy present the comparison is blocked matrix products; without it, pure Python, which is
    fine for a few thousand phrases."""
    n = len(keys)
    if n < 2:
        return []
    best: dict[int, list[tuple[float, int]]] = {}
    try:
        import numpy as np  # optional: the core has no numpy, the build machine usually does
        m = np.asarray(vecs, dtype="float32")
        block = 1024
        for start in range(0, n, block):
            sims = m[start:start + block] @ m.T
            for r in range(sims.shape[0]):
                i = start + r
                row = sims[r]
                row[i] = -1.0
                idx = np.flatnonzero(row >= threshold)
                if idx.size:
                    top = sorted(((float(row[j]), int(j)) for j in idx), reverse=True)[:per_phrase]
                    best[i] = top
    except ImportError:
        for i in range(n):
            cands = []
            for j in range(n):
                if j != i:
                    sim = sum(map(operator.mul, vecs[i], vecs[j]))
                    if sim >= threshold:
                        cands.append((sim, j))
            if cands:
                best[i] = sorted(cands, reverse=True)[:per_phrase]
    pairs = {}
    for i, top in best.items():
        for sim, j in top:
            a, b = (i, j) if i < j else (j, i)
            pairs[(a, b)] = max(pairs.get((a, b), 0.0), round(sim, 4))
    return [(keys[a], keys[b], sim) for (a, b), sim in sorted(pairs.items())]


def build_walk(lake, embedder, *, threshold: float = SYNONYM_THRESHOLD, workers: int = 4) -> dict:
    facts = open_fact_rows(lake)
    phrases: dict[str, str] = {}
    for f in facts:
        for text in (f["s"], f["o"]):
            k = graph.phrase_key(text)
            if k:
                phrases.setdefault(k, text)
    keys = sorted(phrases)
    known = _known_vectors(lake, embedder)
    reused = sum(1 for x in [fact_text(f) for f in facts] + [phrases[k] for k in keys] if x in known)
    partial = {"model": embedder.model, "dim": embedder.dimensions, "checkpoint": True}

    def checkpoint(vectors: dict[str, list[float]]) -> None:
        rows = [{"kind": "checkpoint", "text": x, "vec": v} for x, v in vectors.items()]
        lake.put(layout.WALK_VECTORS, ("\n".join(json.dumps(x) for x in [partial, *rows]) + "\n").encode(),
                 "application/x-ndjson")
    fact_vecs = _embed_all(embedder, [fact_text(f) for f in facts], workers, known=known, checkpoint=checkpoint)
    known.update(zip([fact_text(f) for f in facts], fact_vecs))
    phrase_vecs = _embed_all(embedder, [phrases[k] for k in keys], workers, known=known, checkpoint=checkpoint)
    synonyms = synonym_pairs(keys, phrase_vecs, threshold=threshold)
    g = graph.build_graph(facts, synonyms)
    head = {"model": embedder.model, "dim": embedder.dimensions, "facts": len(facts), "phrases": len(keys),
            "synonyms": len(synonyms), "passages": len(g["passages"]),
            "built_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds")}
    rows = [{"kind": "fact", **{k: f[k] for k in ("s", "p", "o", "pid", "doc")}, "grounded": f.get("grounded", True), "vec": v}
            for f, v in zip(facts, fact_vecs)]
    rows += [{"kind": "phrase", "key": k, "text": phrases[k], "vec": v} for k, v in zip(keys, phrase_vecs)]
    lake.put(layout.WALK_VECTORS, ("\n".join(json.dumps(x) for x in [head, *rows]) + "\n").encode(), "application/x-ndjson")
    lake.put(layout.WALK_GRAPH, json.dumps({**head, **g}).encode(), "application/json")
    _cache.clear()
    return {**{k: head[k] for k in ("facts", "phrases", "synonyms", "passages", "model", "dim")}, "reused": reused}


def has_walk(lake) -> bool:
    return lake is not None and lake.exists(layout.WALK_GRAPH)


def _lake_key(lake) -> tuple:
    return tuple(sorted((k, str(v)) for k, v in vars(lake).items() if isinstance(v, (str, os.PathLike))))


def load_walk(lake) -> dict:
    """The graph, the facts with their vectors, and the passage vectors, cached for a minute."""
    key = _lake_key(lake)
    hit = _cache.get(key)
    if hit is None or time.monotonic() - hit[0] > CACHE_S:
        g = json.loads(lake.get(layout.WALK_GRAPH))
        rows = [json.loads(line) for line in lake.get(layout.WALK_VECTORS).decode().splitlines() if line.strip()]
        facts = [r for r in rows[1:] if r.get("kind") == "fact"]
        passages = {r["id"]: r for r in read_vectors(lake)[1]}
        hit = _cache[key] = (time.monotonic(), {"graph": g, "facts": facts, "passages": passages})
    return hit[1]


def _dot(a: list[float], b: list[float]) -> float:
    return sum(map(operator.mul, a, b))


def related(lake, query: str, *, embedder, limit: int = 8, private: bool = False, keep=None,
            top_facts: int = TOP_FACTS) -> dict:
    """The passages most connected to the question, best first, with the facts that seeded the walk."""
    if not has_walk(lake):
        return {"error": "this collection has no walk yet: run `knowledge-store facts` then `knowledge-store walk`"}
    held = load_walk(lake)
    passages = held["passages"]
    visible = {pid for pid, r in passages.items() if private or r.get("scope", "public") == "public"}
    q = embedder.embed([(query or "")[:1000]])[0]
    scored = sorted(((_dot(q, f["vec"]), f) for f in held["facts"] if f["pid"] in visible),
                    key=lambda x: x[0], reverse=True)[:top_facts]
    hits = [(f, s) for s, f in scored if s > 0]
    if keep is not None and hits:
        kept = keep(query, [f for f, _ in hits])
        hits = [h for h, k in zip(hits, kept) if k] or hits
    passage_hits = [(pid, _dot(q, r["vec"])) for pid, r in passages.items() if pid in visible]
    seeds = graph.seeds_from(hits, passage_hits)
    scores = graph.personalized_pagerank(held["graph"]["edges"], seeds)
    top = graph.rank_passages(scores, allowed=visible, limit=max(1, min(int(limit or 8), 15)))
    out = []
    for pid, score in top:
        r = passages.get(pid) or {}
        out.append({"id": pid, "doc": r.get("doc"), "title": r.get("title"), "text": r.get("text"),
                    "score": round(score, 5), "source_uri": r.get("source_uri") or None})
    return {"passages": out, "method": "walk",
            "via": [{"fact": fact_text(f), "passage": f["pid"], "score": round(s, 4)} for f, s in hits]}


def keep_with_model(client, model_id: str):
    """HippoRAG 2's recognition memory as a keep callable: one small call that says which of the
    retrieved facts bear on the question. On any failure every fact is kept."""
    def keep(question: str, facts: list[dict]) -> list[bool]:
        lines = "\n".join(f"{i + 1}. {fact_text(f)}" for i, f in enumerate(facts))
        prompt = (f"Question: {question}\n\nFacts:\n{lines}\n\nWhich facts could help answer the question, "
                  "directly or as a step towards it? Answer with their numbers separated by commas, or 'none'.")
        try:
            resp = client.converse(modelId=model_id, messages=[{"role": "user", "content": [{"text": prompt}]}],
                                   inferenceConfig={"maxTokens": 100, "temperature": 0})
            text = " ".join(b.get("text", "") for b in resp["output"]["message"]["content"])
            chosen = {int(x) for x in re.findall(r"\d+", text)}
            return [(i + 1) in chosen for i in range(len(facts))] if chosen else [True] * len(facts)
        except Exception:
            return [True] * len(facts)
    return keep
