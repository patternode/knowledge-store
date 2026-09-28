"""Project: gold -> the portal's index, for the active version.

The RDF in gold is the record. This step projects it (the union of every document's graph
along the active version's chain) into a few JSON files the portal API serves:

    summary.json    profile, version history, counts per class and property, top candidates
    ontology.json   the active ontology's terms
    entities.json   every entity with its types, names, attributes, relations and citations
    passages.json   the text of every cited passage
    docs.json       the documents

The projection is disposable and rebuilt in full each run. It holds everything in memory,
which is right for a lab (tens of thousands of entities) and wrong beyond it; the store for a
larger collection is a SPARQL server loaded from the same N-Quads (Oxigraph in a container,
or Neptune via the knowledge-graph module), behind the same API.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from collections import Counter, defaultdict

from rdflib import RDF, RDFS, Dataset, Literal
from rdflib.namespace import SKOS

from .. import layout
from ..config import load_profile, load_sources
from ..extract.rdf import data_base
from ..ontology import model, versions
from ..ontology.model import KL
from ..store import Store, put_json
from .refine import load_doc, load_passages

log = logging.getLogger("project")


def _short(iri: str, base: str) -> str:
    return iri[len(base):] if iri.startswith(base) else iri


def scoped_candidate(term: dict, docs: dict, lake: Store) -> dict:
    """A register entry with each piece of evidence tagged with its document's scope, so the API
    can withhold private evidence (verbatim text) from callers outside the private scope."""
    def scope_of(doc_id: str) -> str:
        if doc_id in docs:
            return docs[doc_id].get("scope", "public")
        return load_doc(lake, doc_id).get("scope", "public") if lake.exists(layout.doc_key(doc_id)) else "private"
    ev = [{**e, "scope": scope_of(e["doc_id"])} for e in term.get("evidence") or []]
    return {**term, "evidence": ev, "scope": "public" if any(e["scope"] == "public" for e in ev) else "private"}


def project(lake: Store) -> dict | None:
    version = versions.active_version(lake)
    if not version:
        return None
    spec, _ = versions.load_version(lake, version)
    chain = versions.chain(lake, version)
    base = data_base(spec)
    ds = Dataset(default_union=True)
    doc_ids: set[str] = set()
    for v in chain:
        for key in lake.list(f"{layout.gold_prefix(v)}/graph/"):
            if key.endswith(".nq"):
                ds.parse(data=lake.get(key).decode(), format="nquads")
                doc_ids.add(layout.doc_id_from_key(key))

    docs = {}
    for d in sorted(doc_ids):
        if lake.exists(layout.doc_key(d)):
            meta = load_doc(lake, d)
            docs[d] = {"title": meta.get("title"), "name": meta.get("name"), "source": meta.get("source"),
                       "scope": meta.get("scope", "public"), "passages": meta.get("passages"),
                       "format": (meta.get("parser") or "text@1").split("@")[0]}

    passage_doc: dict[str, str] = {}
    for p, _, doc in ds.triples((None, KL.partOf, None)):
        passage_doc[str(p)] = _short(str(doc), base + "doc/")

    entities: dict[str, dict] = {}
    for s in set(ds.subjects(KL.mentionedIn, None)):
        iri = str(s)
        types = sorted({model.local_name(t) for t in ds.objects(s, RDF.type)
                        if str(t).startswith(spec.namespace) and model.local_name(t) in spec.classes})
        if not types:
            continue
        most = [t for t in types if not any(t != u and spec.is_a(u, t) for u in types)]
        pids = sorted({_short(str(p), base + "passage/") for p in ds.objects(s, KL.mentionedIn)})
        edocs = sorted({passage_doc.get(base + "passage/" + p, "") for p in pids} - {""})
        entities[iri] = {"id": _short(iri, base), "type": most[0], "types": types,
                         "label": str(ds.value(s, RDFS.label) or iri.rsplit("/", 1)[-1]),
                         "aliases": sorted({str(a) for a in ds.objects(s, SKOS.altLabel)}),
                         "attributes": [], "out": [], "in": [], "passages": pids, "docs": edocs,
                         "scope": "public" if any(docs.get(d, {}).get("scope") == "public" for d in edocs) else "private"}

    cited: set[str] = set()
    prop_counts: Counter = Counter()
    seen: set[tuple] = set()
    for a in set(ds.subjects(RDF.type, KL.Assertion)):
        s, p, o = ds.value(a, RDF.subject), ds.value(a, RDF.predicate), ds.value(a, RDF.object)
        if s is None or p is None or o is None or str(s) not in entities:
            continue
        pids = sorted({_short(str(x), base + "passage/") for x in ds.objects(a, KL.extractedFrom)})
        cited |= set(pids)
        local = model.local_name(p)
        key = (str(s), local, str(o))
        if key in seen:  # the same fact from two documents: merge the citations
            for row in entities[str(s)]["attributes"] + entities[str(s)]["out"]:
                if row["p"] == local and (row.get("v") == str(o) or row.get("o") == _short(str(o), base)):
                    row["passages"] = sorted(set(row["passages"]) | set(pids))
            continue
        seen.add(key)
        prop_counts[local] += 1
        if isinstance(o, Literal):
            entities[str(s)]["attributes"].append({"p": local, "v": str(o), "passages": pids})
        elif str(o) in entities:
            entities[str(s)]["out"].append({"p": local, "o": _short(str(o), base), "passages": pids})
            entities[str(o)]["in"].append({"p": local, "s": _short(str(s), base), "passages": pids})
    for e in entities.values():
        cited |= set(e["passages"])

    passages = {}
    by_doc: dict[str, set[str]] = defaultdict(set)
    for pid in cited:
        d = passage_doc.get(base + "passage/" + pid)
        if d:
            by_doc[d].add(pid)
    for d, pids in by_doc.items():
        for p in load_passages(lake, d):
            if p.passage_id in pids:
                passages[p.passage_id] = {"doc": d, "seq": p.seq, "text": p.text,
                                          "scope": docs.get(d, {}).get("scope", "public")}

    class_counts: Counter = Counter()
    for e in entities.values():
        for t in {a for t in e["types"] for a in spec.ancestors(t)}:
            class_counts[t] += 1
    reg = json.loads(lake.get(layout.CANDIDATE_REGISTER)) if lake.exists(layout.CANDIDATE_REGISTER) else {"terms": []}
    history = []
    for v in versions.published_versions(lake):
        m = versions.manifest(lake, v)
        history.append({"version": v, "kind": m["kind"], "base": m.get("base"), "published_at": m.get("published_at"),
                        "counts": m.get("counts"), "note": m.get("note"), "in_chain": v in chain})
    ontology = {
        "namespace": spec.namespace, "version": version, "label": spec.label,
        "classes": [{"name": c.local, "label": c.label, "definition": c.definition, "synonyms": list(c.alt_labels),
                     "parents": list(c.parents), "count": class_counts.get(c.local, 0)}
                    for c in sorted(spec.classes.values(), key=lambda t: t.local)],
        "relations": [{"name": p.local, "label": p.label, "definition": p.definition, "domain": list(p.domain),
                       "range": list(p.range), "count": prop_counts.get(p.local, 0)}
                      for p in sorted(spec.relations.values(), key=lambda t: t.local)],
        "attributes": [{"name": p.local, "label": p.label, "definition": p.definition, "domain": list(p.domain),
                        "datatype": p.range[0] if p.range else "string", "count": prop_counts.get(p.local, 0)}
                       for p in sorted(spec.attributes.values(), key=lambda t: t.local)],
    }
    profile = load_profile(lake)
    summary = {
        "profile": profile.to_dict(), "version": version, "chain": chain, "history": history,
        "sources": [{"name": s.name, "type": s.type, "scope": s.scope} for s in load_sources(lake)],
        "counts": {"documents": len(docs), "entities": len(entities), "facts": sum(prop_counts.values()),
                   "passages": len(passages), "silver_documents": sum(1 for _ in lake.list(layout.SILVER_DOCS + "/"))},
        "candidates": [scoped_candidate(t, docs, lake) for t in reg["terms"][:60]],
        "built_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
    }
    for name, obj in (("summary", summary), ("ontology", ontology), ("entities", list(entities.values())),
                      ("passages", passages), ("docs", docs)):
        put_json(lake, layout.index_key(version, name), obj)
    log.info("projected %s: %d documents, %d entities, %d facts", version, len(docs), len(entities),
             sum(prop_counts.values()))
    return summary["counts"]
