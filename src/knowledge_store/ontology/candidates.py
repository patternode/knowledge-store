"""Candidate terms: what extraction found that the ontology has no word for.

Every extraction writes the candidates it saw (gold/<version>/candidates/<doc>.jsonl). The
register aggregates them across documents by normalised term, with document counts and
evidence, and marks those that are already covered by a synonym of an existing term (a hint
that a synonym, not a term, is missing).

Questions add to it too. When the chat cannot answer, the workbench's analyst proposes the terms
it would need, and a curator can keep its report as an ontology request (knowledge_store.workbench).
Each requested term joins the register with how many requests asked for it and the questions
behind them, and a revision considers it even if no document has used it yet: a person asked.

A revision proposal feeds the register to the consolidation step with the current ontology in
context, and writes a draft next version as a minor bump (additions only; the prompt keeps
existing terms unchanged). The draft is diffed against the active version, so the curator
sees the change class and the bump it needs before publishing. Nothing reaches the ontology
without a person publishing it: candidates come from document text, which is untrusted input.
"""

from __future__ import annotations

import datetime as dt
import json
from collections import defaultdict

from .. import layout, workbench
from ..config import Profile
from ..store import Store, put_json
from . import discover, model, versions, writer

MIN_DOCS = 2


def build_register(lake: Store, version: str) -> dict:
    spec, _ = versions.load_version(lake, version)
    idx = spec.synonym_index
    terms: dict[tuple[str, str], dict] = {}
    for key in lake.list(f"{layout.gold_prefix(version)}/candidates/"):
        doc_id = layout.doc_id_from_key(key)
        for line in lake.get(key).decode().splitlines():
            if not line.strip():
                continue
            c = json.loads(line)
            k = (c["kind"], model.normalise(c["term"]))
            t = terms.setdefault(k, {"kind": c["kind"], "term": c["term"], "names": set(), "docs": set(),
                                     "definitions": [], "evidence": [], "nearest": defaultdict(int)})
            t["names"].add(c["term"])
            t["docs"].add(doc_id)
            if len(t["definitions"]) < 3 and c.get("definition") and c["definition"] not in t["definitions"]:
                t["definitions"].append(c["definition"])
            if len(t["evidence"]) < 5:
                t["evidence"].append({"doc_id": doc_id, "text": c.get("evidence"), "passage_ids": c.get("passage_ids")})
            if c.get("nearest"):
                t["nearest"][c["nearest"]] += 1
    rows = []
    for (kind, norm), t in terms.items():
        rows.append({"kind": kind, "term": t["term"], "also": sorted(t["names"] - {t["term"]}),
                     "docs": len(t["docs"]), "definitions": t["definitions"], "evidence": t["evidence"],
                     "nearest": max(t["nearest"], key=t["nearest"].get) if t["nearest"] else None,
                     "covered_by": idx.get(norm), "asked": 0, "questions": []})
    by_key = {(r["kind"], model.normalise(r["term"])): r for r in rows}
    for q in workbench.requested_terms(lake):
        r = by_key.get((q["kind"], model.normalise(q["term"])))
        if r is None:
            r = {"kind": q["kind"], "term": q["term"], "also": [], "docs": 0, "definitions": [], "evidence": [],
                 "nearest": q["nearest"], "covered_by": idx.get(model.normalise(q["term"])), "asked": 0, "questions": []}
            rows.append(r)
            by_key[(q["kind"], model.normalise(q["term"]))] = r
        r["asked"] += q["asked"]
        r["questions"] = (r["questions"] + q["questions"])[:5]
        r["definitions"] = (r["definitions"] + [d for d in q["definitions"] if d not in r["definitions"]])[:3]
    rows.sort(key=lambda r: (-r["docs"], -r["asked"], r["kind"], r["term"]))
    reg = {"version": version, "built_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
           "documents": len({e["doc_id"] for r in rows for e in r["evidence"]}), "terms": rows}
    put_json(lake, layout.CANDIDATE_REGISTER, reg)
    return reg


def propose_revision(client, model_id: str, lake: Store, profile: Profile, *, min_docs: int = MIN_DOCS,
                     draft_id: str | None = None) -> dict:
    active = versions.active_version(lake)
    if not active:
        raise ValueError("no active ontology: run discovery and publish a version first")
    reg = build_register(lake, active)
    keep = [t for t in reg["terms"] if (t["docs"] >= min_docs or t.get("asked")) and not t["covered_by"]]
    if not keep:
        return {"kind": "revision", "status": "nothing_to_propose", "register_terms": len(reg["terms"])}
    prior, _ = versions.load_version(lake, active)
    kinds = {"class": "classes", "relation": "relations", "attribute": "attributes"}
    agg = {k: [] for k in discover.KINDS}
    for t in keep:
        agg[kinds[t["kind"]]].append({"name": t["term"], "also": t["also"], "docs": t["docs"], "stability": 1.0,
                                      "definitions": t["definitions"],
                                      "examples": [e["text"] for e in t["evidence"][:3]]
                                      + [f"asked: {q}" for q in t.get("questions", [])[:2]], "nearest": t["nearest"]})
    defn, usage = discover.consolidate(client, model_id, agg, profile, prior=prior,
                                       target_classes=len(prior.classes) + 5)
    major, minor, _ = map(int, active.split("."))
    version = f"{major}.{minor + 1}.0"
    ttl = writer.ontology_ttl(defn, namespace=prior.namespace, version=version, label=prior.label or profile.name,
                              comment=f"Revision proposed {dt.date.today().isoformat()} from {len(keep)} candidate "
                                      f"terms seen in at least {min_docs} documents or asked for in an ontology request. "
                                      "Curate before publishing.",
                              prior=prior)
    spec = model.load(data=ttl)
    d = versions.diff(prior, spec)
    draft_id = draft_id or dt.datetime.now(dt.UTC).strftime("revise-%Y%m%dT%H%M%S")
    report = {"draft_id": draft_id, "kind": "revision", "base": active, "proposed_version": version,
              "diff": d.to_dict(), "required_bump": versions.required_bump(d.kind),
              "candidates_used": keep, "rejected": defn.get("rejected") or [], "usage": usage}
    if d.kind in ("semantic", "removal"):
        report["warning"] = ("the proposal changes existing terms, which the prompt forbids; review the diff. "
                             "Publishing it needs a major version and a full re-extraction.")
    discover.write_draft(lake, draft_id, ttl, writer.shapes_ttl(spec), report)
    return report
