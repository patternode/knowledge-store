"""Ontology discovery: propose a first ontology from a sample of the collection.

The method follows EDC (extract, define, canonicalise; Zhang and Soh, EMNLP 2024), in three steps:

1. Open proposal. For each sampled document the model proposes the entity types, relations
   and attributes its passages contain, each with a definition and verbatim examples.
   Examples not found in their passage are dropped (grounding).
2. Aggregate. Proposals are merged by normalised name and counted by document. With
   resamples > 1 the whole of step 1 is repeated on different samples, and each type's
   stability is the share of resamples that proposed it. Nothing in the literature measures
   run-to-run variance of LLM ontology induction, so this lab measures it for itself.
3. Consolidate. One call sees the aggregated proposals with their counts and stability, and
   defines a small ontology: merges synonyms, picks parents, fixes domains and ranges, and
   says what it rejected and why.
4. Review (review.py, on unless review=False). One more call sees the consolidated draft with
   each term's document support and returns edits (parents, merges, drops, domains, ranges,
   datatypes), each with a reason, which are applied deterministically and recorded in the
   report. Drafts come out of step 3 flat and with near-duplicates; this is the first pass at
   fixing that, before a person does.

The output is a draft (ontology/drafts/<id>/): ontology.ttl, shapes.ttl and report.json. In curated
mode a person curates it in git and publishes it (versions.py); in auto mode the sweep publishes
it as 0.1.0, provisional, so the reviewed draft is what extraction first uses.

Discovery reads a sample, not the collection, because it is the expensive, unbounded step: its
cost is set by sample_docs x resamples, whatever the collection's size.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import random
from collections import defaultdict

from .. import layout
from ..config import Profile
from ..llm import decode_tool_input
from ..pipeline.refine import load_doc, load_passages, silver_doc_ids
from ..store import Store, put_json
from . import model, writer
from . import review as reviewer

log = logging.getLogger("discover")

PROPOSE_TOOL = "propose_types"
DEFINE_TOOL = "define_ontology"
PROMPT_VERSION = "kl-discover-v1"
PASSAGES_PER_DOC = 8
KINDS = ("classes", "relations", "attributes")

PROPOSE_SYSTEM = """You are helping design an ontology for a collection of documents.

{profile}

Read the passages and propose the types of thing they talk about, the relations between those things,
and the attributes those things have. Propose general, reusable types ("Organisation", "Clinical trial"),
not individual things ("Acme Ltd") and not one-off phrases. Give each a one-sentence definition that would
let someone else decide whether a new example belongs, and one to three examples copied verbatim from a
passage, with its passage id. Prefer a few well-defined types to many overlapping ones."""

DEFINE_SYSTEM = """You are designing a small, usable ontology for a collection of documents, from types
proposed by reading a sample of it.

{profile}

You get the proposed classes, relations and attributes with how many sampled documents proposed each
(docs) and, when several samples were drawn, the share of samples that proposed it (stability).

Design the ontology:
- Merge proposals that mean the same thing; keep the clearest name and list the others as synonyms.
- Keep a type only if it would be useful for questions about this collection and is well supported.
  Proposals seen once, or with low stability, are usually noise; keep them only if clearly central.
- Arrange classes in a shallow hierarchy with parents where one class is a kind of another.
- Every relation needs a domain and a range among your classes. Every attribute needs a domain and
  a datatype (string, decimal, integer, date, boolean).
- Aim for roughly {target} classes. Say what you rejected and why.
{existing}"""


def _propose_tool() -> dict:
    ex = {"type": "array", "items": {"type": "object", "required": ["text", "passage_id"],
          "properties": {"text": {"type": "string", "description": "verbatim from the passage"},
                         "passage_id": {"type": "string"}}}}
    item = lambda extra: {"type": "object", "required": ["name", "definition", "examples"],  # noqa: E731
                          "properties": {"name": {"type": "string"}, "definition": {"type": "string"},
                                         **extra, "examples": ex}}
    return {"toolSpec": {"name": PROPOSE_TOOL, "description": "Propose the ontology terms these passages contain.",
            "inputSchema": {"json": {"type": "object", "required": ["classes"], "properties": {
                "classes": {"type": "array", "items": item({})},
                "relations": {"type": "array", "items": item({
                    "subject_type": {"type": "string"}, "object_type": {"type": "string"}})},
                "attributes": {"type": "array", "items": item({
                    "entity_type": {"type": "string"},
                    "datatype": {"type": "string", "enum": list(model.DATATYPES)}})},
            }}}}}


def _define_tool() -> dict:
    term = {"name": {"type": "string"}, "label": {"type": "string"}, "definition": {"type": "string"},
            "synonyms": {"type": "array", "items": {"type": "string"}},
            "merged_from": {"type": "array", "items": {"type": "string"}}}
    return {"toolSpec": {"name": DEFINE_TOOL, "description": "Define the consolidated ontology.",
            "inputSchema": {"json": {"type": "object", "required": ["classes", "relations", "attributes", "rejected"],
                "properties": {
                    "classes": {"type": "array", "items": {"type": "object", "required": ["name", "definition"],
                                "properties": {**term, "parent": {"type": ["string", "null"]}}}},
                    "relations": {"type": "array", "items": {"type": "object",
                                  "required": ["name", "definition", "domain", "range"],
                                  "properties": {**term, "domain": {"type": "string"}, "range": {"type": "string"}}}},
                    "attributes": {"type": "array", "items": {"type": "object",
                                   "required": ["name", "definition", "domain", "datatype"],
                                   "properties": {**term, "domain": {"type": "string"},
                                                  "datatype": {"type": "string", "enum": list(model.DATATYPES)}}}},
                    "rejected": {"type": "array", "items": {"type": "object", "required": ["name", "reason"],
                                 "properties": {"name": {"type": "string"}, "reason": {"type": "string"}}}},
                }}}}}


def _call(client, model_id: str, system: str, user: str, tool: dict, max_tokens: int = 16000) -> tuple[dict, dict]:
    resp = client.converse(modelId=model_id, system=[{"text": system}],
                           messages=[{"role": "user", "content": [{"text": user}]}],
                           toolConfig={"tools": [tool], "toolChoice": {"tool": {"name": tool["toolSpec"]["name"]}}},
                           inferenceConfig={"maxTokens": max_tokens, "temperature": 0})
    for block in resp["output"]["message"]["content"]:
        if "toolUse" in block:
            return decode_tool_input(block["toolUse"]["input"], tool["toolSpec"]["inputSchema"]["json"]), resp.get("usage", {})
    raise RuntimeError(f"model did not call {tool['toolSpec']['name']} (stopReason {resp.get('stopReason')})")


def sample_docs(lake: Store, n: int, seed: int) -> list[str]:
    """n documents, spread across sources: round-robin over sources in random order."""
    by_source: dict[str, list[str]] = defaultdict(list)
    for doc_id in silver_doc_ids(lake):
        by_source[load_doc(lake, doc_id)["source"]].append(doc_id)
    rng = random.Random(seed)
    pools = [rng.sample(v, len(v)) for _, v in sorted(by_source.items())]
    out: list[str] = []
    while len(out) < n and any(pools):
        for pool in pools:
            if pool and len(out) < n:
                out.append(pool.pop())
    return out


def _passages_for(lake: Store, doc_id: str, seed: int):
    ps = load_passages(lake, doc_id)
    if len(ps) <= PASSAGES_PER_DOC:
        return ps
    rng = random.Random(seed)
    keep = sorted({0, 1, *rng.sample(range(2, len(ps)), PASSAGES_PER_DOC - 2)})
    return [ps[i] for i in keep]


def propose(client, model_id: str, lake: Store, doc_ids: list[str], profile: Profile, seed: int) -> tuple[list[dict], dict]:
    """Step 1 for a set of documents: grounded proposals, one list per document."""
    system = PROPOSE_SYSTEM.format(profile=profile.prompt_context())
    tool = _propose_tool()
    usage: dict = defaultdict(int)
    out = []
    for doc_id in doc_ids:
        doc = load_doc(lake, doc_id)
        ps = _passages_for(lake, doc_id, seed)
        text = {p.passage_id: " ".join(p.text.lower().split()) for p in ps}
        user = f"Document: {doc.get('title') or doc_id}\n\n" + "\n".join(
            f"<passage id=\"{p.passage_id}\">\n{p.text}\n</passage>" for p in ps)
        try:
            res, u = _call(client, model_id, system, user, tool)
        except Exception as e:
            log.warning("%s: proposal failed: %r", doc_id[:12], e)
            continue
        for k, v in u.items():
            if isinstance(v, int):
                usage[k] += v
        for kind in KINDS:
            kept = []
            for t in res.get(kind) or []:
                if not isinstance(t, dict):
                    continue
                exs = [x for x in t.get("examples") or [] if isinstance(x, dict)
                       and " ".join(str(x.get("text", "")).lower().split()) in text.get(x.get("passage_id"), "")]
                if exs and str(t.get("name") or "").strip():
                    kept.append({**t, "examples": exs})
            res[kind] = kept
        out.append({"doc_id": doc_id, **{k: res.get(k) or [] for k in KINDS}})
    return out, dict(usage)


def aggregate(rounds: list[list[dict]]) -> dict[str, list[dict]]:
    """Step 2: merge by normalised name; count documents; stability across rounds."""
    agg: dict[str, dict[str, dict]] = {k: {} for k in KINDS}
    for r, proposals in enumerate(rounds):
        for p in proposals:
            for kind in KINDS:
                for t in p[kind]:
                    key = model.normalise(t["name"])
                    a = agg[kind].setdefault(key, {"name": t["name"], "names": set(), "definitions": [],
                                                   "docs": set(), "rounds": set(), "examples": [],
                                                   "signatures": defaultdict(int)})
                    a["names"].add(t["name"])
                    a["docs"].add(p["doc_id"])
                    a["rounds"].add(r)
                    if t.get("definition") and len(a["definitions"]) < 3:
                        a["definitions"].append(t["definition"])
                    if len(a["examples"]) < 3:
                        a["examples"] += [x["text"] for x in t["examples"][:1]]
                    sig = (t.get("subject_type"), t.get("object_type")) if kind == "relations" else \
                          (t.get("entity_type"), t.get("datatype")) if kind == "attributes" else None
                    if sig:
                        a["signatures"][" -> ".join(str(s) for s in sig)] += 1
    n = max(1, len(rounds))
    out = {}
    for kind in KINDS:
        rows = []
        for a in agg[kind].values():
            rows.append({"name": a["name"], "also": sorted(a["names"] - {a["name"]}), "docs": len(a["docs"]),
                         "stability": round(len(a["rounds"]) / n, 2), "definitions": a["definitions"],
                         "examples": a["examples"][:3],
                         "signature": max(a["signatures"], key=a["signatures"].get) if a["signatures"] else None})
        out[kind] = sorted(rows, key=lambda x: (-x["stability"], -x["docs"], x["name"]))
    return out


def stability_jaccard(rounds: list[list[dict]], kind: str = "classes") -> float | None:
    """Mean pairwise Jaccard overlap of the normalised type names proposed in each round."""
    sets = [{model.normalise(t["name"]) for p in r for t in p[kind]} for r in rounds]
    pairs = [(a, b) for i, a in enumerate(sets) for b in sets[i + 1:]]
    if not pairs:
        return None
    return round(sum(len(a & b) / len(a | b) if a | b else 1.0 for a, b in pairs) / len(pairs), 3)


def consolidate(client, model_id: str, aggregated: dict, profile: Profile, *, target_classes: int = 15,
                prior: model.OntologySpec | None = None, max_items: int = 150) -> tuple[dict, dict]:
    """Step 3. With prior, the call extends an existing ontology instead of starting afresh."""
    existing = ""
    if prior is not None:
        existing = ("\nAn ontology already exists (below). Keep every existing term unchanged. Map a proposal to an "
                    "existing term when it means the same (add it as a synonym there), and add new terms only for "
                    "what the existing ontology cannot express. Give existing terms by their current names.\n\n"
                    + prior.vocabulary_prompt())
    system = DEFINE_SYSTEM.format(profile=profile.prompt_context(), target=target_classes, existing=existing)
    trimmed = {k: v[:max_items] for k, v in aggregated.items()}
    return _call(client, model_id, system, json.dumps(trimmed, indent=1, default=list), _define_tool(), 32000)


def discover(client, model_id: str, lake: Store, profile: Profile, *, sample: int = 20, resamples: int = 1,
             seed: int = 7, target_classes: int = 15, version: str = "0.1.0", draft_id: str | None = None,
             review: bool = True) -> dict:
    draft_id = draft_id or dt.datetime.now(dt.UTC).strftime("discover-%Y%m%dT%H%M%S")
    rounds, usage = [], defaultdict(int)
    for r in range(resamples):
        ids = sample_docs(lake, sample, seed + r)
        if not ids:
            raise ValueError("no refined documents to discover from: ingest and refine first")
        props, u = propose(client, model_id, lake, ids, profile, seed + r)
        rounds.append(props)
        for k, v in u.items():
            usage[k] += v
    agg = aggregate(rounds)
    defn, u = consolidate(client, model_id, agg, profile, target_classes=target_classes)
    for k, v in u.items():
        if isinstance(v, int):
            usage[k] += v
    reviewed = None
    if review:
        try:
            edits, u = reviewer.review(client, model_id, defn, agg, profile)
            for k, v in u.items():
                if isinstance(v, int):
                    usage[k] += v
            defn, applied, skipped = reviewer.apply_edits(defn, edits)
            reviewed = {"prompt_version": reviewer.PROMPT_VERSION, "applied": applied, "skipped": skipped}
        except Exception as e:  # a failed review leaves the draft as consolidation made it
            log.warning("review failed, keeping the consolidated draft: %r", e)
            reviewed = {"prompt_version": reviewer.PROMPT_VERSION, "error": repr(e)[:300]}
    evidence = {writer.class_name(t["name"]): t["docs"] for t in agg["classes"]}
    ttl = writer.ontology_ttl(defn, namespace=profile.ontology_base, version=version,
                              label=f"{profile.name} ontology",
                              comment=f"Discovered {dt.date.today().isoformat()} from {sample} documents x "
                                      f"{resamples} samples ({draft_id}). Curate before publishing.",
                              evidence=evidence)
    spec = model.load(data=ttl)
    report = {"draft_id": draft_id, "kind": "discovery", "prompt_version": PROMPT_VERSION, "model_id": model_id,
              "sample": sample, "resamples": resamples, "seed": seed,
              "stability_jaccard": {k: stability_jaccard(rounds, k) for k in KINDS},
              "documents": sorted({p["doc_id"] for r in rounds for p in r}),
              "aggregated": agg, "rejected": defn.get("rejected") or [], "review": reviewed, "usage": dict(usage),
              "counts": {"classes": len(spec.classes), "relations": len(spec.relations), "attributes": len(spec.attributes)}}
    write_draft(lake, draft_id, ttl, writer.shapes_ttl(spec), report)
    return report


def write_draft(lake: Store, draft_id: str, ttl: str, shapes: str, report: dict) -> None:
    pre = f"{layout.ONTOLOGY_DRAFTS}/{draft_id}"
    lake.put(f"{pre}/ontology.ttl", ttl.encode(), "text/turtle")
    lake.put(f"{pre}/shapes.ttl", shapes.encode(), "text/turtle")
    put_json(lake, f"{pre}/report.json", report)
