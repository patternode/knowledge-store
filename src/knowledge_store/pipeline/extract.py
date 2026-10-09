"""Extract: silver -> gold, against the active ontology version.

Which work a document needs depends on the active version's kind and on what gold already holds:

    no gold anywhere in the version's chain  -> full extraction at the active version
    held at a base version, active additive  -> delta extraction of the added terms, if selected
    held at a base version, active descriptive -> nothing (labels changed, facts did not)

A document is done at a version when gold/<version>/extractions/<doc>.json exists, whatever
its status (extracted, rejected, not_selected), so a sweep never pays for the same document
twice. --retry-rejected and --reselect redo those deliberately.

Delta selection is a heuristic, and the README says so: a document is selected when its
candidates name a new term, when its passages contain a new term's label or synonym, or when
it holds entities of a class that gained a subclass (they may need retyping). A new term can
apply to a document none of these catch; --all-delta runs the delta over every document.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

from rdflib import RDF, RDFS, Dataset

from .. import layout, ledger
from ..config import Profile
from ..extract.extractor import ExtractionOutcome, Extractor, run_record
from ..extract.rdf import Iris, to_nquads
from ..ontology import model, versions
from ..ontology.model import KL
from ..store import Store, put_json
from .refine import load_doc, load_passages, silver_doc_ids

log = logging.getLogger("extract")


def _done(lake: Store, version: str, doc_id: str) -> dict | None:
    key = layout.extraction_key(version, doc_id)
    return json.loads(lake.get(key)) if lake.exists(key) else None


def held_at(lake: Store, chain: list[str], doc_id: str) -> list[str]:
    """The versions in chain at which gold holds a graph for the document."""
    return [v for v in chain if lake.exists(layout.graph_key(v, doc_id))]


def known_entities(lake: Store, spec: model.OntologySpec, versions_held: list[str], doc_id: str) -> dict[str, dict]:
    """ref -> {iri, type, name} for the entities already held for a document."""
    ds = Dataset(default_union=True)
    for v in versions_held:
        ds.parse(data=lake.get(layout.graph_key(v, doc_id)).decode(), format="nquads")
    ents: dict[str, dict] = {}
    for s in sorted(set(ds.subjects(KL.mentionedIn, None, unique=True)), key=str):
        types = [model.local_name(t) for t in ds.objects(s, RDF.type) if str(t).startswith(spec.namespace)]
        types = [t for t in types if t in spec.classes]
        name = ds.value(s, RDFS.label)
        if types and name:
            # the most specific type: one that is not an ancestor of another
            best = next((t for t in types if not any(t != u and spec.is_a(u, t) for u in types)), types[0])
            ents[str(s)] = {"iri": str(s), "type": best, "name": str(name)}
    return {f"k{i + 1}": v for i, v in enumerate(ents.values())}


def select_for_delta(lake: Store, spec: model.OntologySpec, delta_terms: list[str], chain: list[str],
                     doc_id: str, held: list[str]) -> str | None:
    """Why a document is selected for a delta run, or None."""
    names = {model.normalise(n) for t in delta_terms if spec.term(t) for n in spec.term(t).names()}
    for v in held:
        key = layout.candidates_key(v, doc_id)
        if lake.exists(key):
            for line in lake.get(key).decode().splitlines():
                if line.strip() and model.normalise(json.loads(line)["term"]) in names:
                    return "candidate"
    text = " ".join(p.text.lower() for p in load_passages(lake, doc_id))
    norm_text = " " + model.normalise(text) + " "
    if any(f" {n} " in norm_text for n in names if n):
        return "lexical"
    parents = {p for t in delta_terms if t in spec.classes for p in spec.classes[t].parents}
    if parents:
        known = known_entities(lake, spec, held, doc_id)
        if any(spec.is_a(k["type"], p) for k in known.values() for p in parents):
            return "retype"
    return None


def extract_one(lake: Store, extractor: Extractor, version: str, doc_id: str, run: dict,
                known: dict[str, dict] | None = None) -> dict:
    doc = load_doc(lake, doc_id)
    passages = load_passages(lake, doc_id)
    ids = Iris(extractor.spec)
    with ledger.subject(doc_id[:16]):
        try:
            out: ExtractionOutcome = extractor.extract(doc, passages, run, known=known)
        except Exception as e:
            row = {"doc_id": doc_id, "status": "rejected", "error": repr(e)[:1000], "run_id": run["run_id"]}
            put_json(lake, layout.rejected_key(version, doc_id), row)
            put_json(lake, layout.extraction_key(version, doc_id), row)
            return row
    lake.put(layout.graph_key(version, doc_id), to_nquads(out.graph, ids.graph(version, doc_id)), "application/n-quads")
    if out.candidates:
        lake.put(layout.candidates_key(version, doc_id),
                 "\n".join(json.dumps(c) for c in out.candidates).encode(), "application/x-ndjson")
    counts = {k: len(out.result.get(k) or []) for k in ("entities", "attributes", "relations")}
    row = {"doc_id": doc_id, "status": "extracted", "run": run, "repairs": out.repairs, "dropped": out.dropped,
           "usage": out.usage, "counts": counts, "candidates": len(out.candidates), "delta": bool(known is not None),
           "result": out.result, "at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds")}
    put_json(lake, layout.extraction_key(version, doc_id), row)
    return {k: v for k, v in row.items() if k != "result"}


def extract_all(lake: Store, client, model_id: str, profile: Profile, *, workers: int = 4,
                limit: int | None = None, retry_rejected: bool = False, all_delta: bool = False,
                run_id: str | None = None) -> list[dict]:
    version = versions.active_version(lake)
    if not version:
        log.info("no active ontology: nothing to extract (run discovery, curate and publish a version)")
        return []
    spec, shapes = versions.load_version(lake, version)
    m = versions.manifest(lake, version)
    chain = versions.chain(lake, version)
    bases = chain[1:]
    run_id = run_id or dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%S-") + uuid.uuid4().hex[:6]
    ledger.set_run("extract", run_id)
    full = Extractor(client, model_id, spec, profile, shapes=shapes)
    delta = (Extractor(client, model_id, spec, profile, shapes=shapes, only=set(m["delta_terms"]))
             if m["kind"] == "additive" and m["delta_terms"] else None)
    from ..structured.bind import mapped_doc_ids
    mapped = mapped_doc_ids(lake)

    todo: list[tuple[str, dict | None, dict]] = []
    rows: list[dict] = []
    for doc_id in silver_doc_ids(lake):
        if doc_id in mapped:
            continue
        prior = _done(lake, version, doc_id)
        if prior and not (retry_rejected and prior["status"] == "rejected"):
            continue
        held = held_at(lake, bases, doc_id)
        if not held:
            todo.append((doc_id, None, run_record(run_id, model_id, version)))
        elif delta is None:
            row = {"doc_id": doc_id, "status": "not_selected", "reason": f"{m['kind']} version: no new terms"}
            put_json(lake, layout.extraction_key(version, doc_id), row)
            rows.append(row)
        else:
            why = "all" if all_delta else select_for_delta(lake, spec, m["delta_terms"], chain, doc_id, held)
            if why:
                known = known_entities(lake, spec, held, doc_id)
                todo.append((doc_id, known, {**run_record(run_id, model_id, version, delta=True), "selected": why}))
            else:
                row = {"doc_id": doc_id, "status": "not_selected", "reason": "no sign of the new terms"}
                put_json(lake, layout.extraction_key(version, doc_id), row)
                rows.append(row)
        if limit is not None and len(todo) >= limit:
            break
    log.info("extract %s at %s (%s): %d documents to extract", run_id, version, m["kind"], len(todo))
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futs = [pool.submit(extract_one, lake, delta if known is not None else full, version, doc_id, run, known)
                for doc_id, known, run in todo]
        for f in as_completed(futs):
            row = f.result()
            rows.append(row)
            log.info("%s %s", row["doc_id"][:12], row["status"])
    return rows
