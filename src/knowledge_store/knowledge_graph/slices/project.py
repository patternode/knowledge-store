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
from urllib.parse import unquote

from rdflib import RDF, RDFS, Dataset, Literal
from rdflib.namespace import SKOS

from knowledge_store.platform_services import layout
from knowledge_store.platform_services import load_profile, load_sources
from knowledge_store.extraction import data_base
from knowledge_store.ontology import model
from knowledge_store.ontology import versions
from knowledge_store.ontology import KL
from knowledge_store.platform_services import Store, put_json
from knowledge_store.ingestion import load_doc, load_passages

log = logging.getLogger("project")


def _short(iri: str, base: str) -> str:
    return iri[len(base):] if iri.startswith(base) else iri


def doc_scope(doc_id: str, docs: dict, lake: Store) -> str:
    if doc_id in docs:
        return docs[doc_id].get("scope", "public")
    return load_doc(lake, doc_id).get("scope", "public") if lake.exists(layout.doc_key(doc_id)) else "private"


def public_terms(lake: Store, version: str, docs: dict) -> dict:
    """(kind, normalised term) -> the names, definitions and documents of a candidate term seen
    in public documents only: what a public caller may see of a register entry."""
    out: dict[tuple, dict] = {}
    for key in lake.list(f"{layout.gold_prefix(version)}/candidates/"):
        doc_id = layout.doc_id_from_key(key)
        if doc_scope(doc_id, docs, lake) != "public":
            continue
        for line in lake.get(key).decode().splitlines():
            if not line.strip():
                continue
            c = json.loads(line)
            t = out.setdefault((c["kind"], model.normalise(c["term"])), {"names": set(), "docs": set(), "definitions": []})
            t["names"].add(c["term"])
            t["docs"].add(doc_id)
            if len(t["definitions"]) < 3 and c.get("definition") and c["definition"] not in t["definitions"]:
                t["definitions"].append(c["definition"])
    return out


def scoped_candidate(term: dict, docs: dict, lake: Store, public: dict | None = None) -> dict:
    """A register entry with each piece of evidence tagged with its document's scope, so the API
    can withhold private evidence (verbatim text) from callers outside the private scope, and with
    what public documents alone say of it (public: term, also, definitions, docs)."""
    ev = [{**e, "scope": doc_scope(e["doc_id"], docs, lake)} for e in term.get("evidence") or []]
    out = {**term, "evidence": ev, "scope": "public" if any(e["scope"] == "public" for e in ev) else "private"}
    p = (public or {}).get((term.get("kind"), model.normalise(term.get("term") or "")))
    if p:
        name = term["term"] if term["term"] in p["names"] else sorted(p["names"])[0]
        out["public"] = {"term": name, "also": sorted(p["names"] - {name}), "definitions": p["definitions"],
                         "docs": len(p["docs"])}
    return out


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
    from knowledge_store.extraction import binding as structured_binding
    for entry in structured_binding(lake, version).values():
        key = entry.get("graph")
        if key and lake.exists(key):
            ds.parse(data=lake.get(key).decode(), format="nquads")

    docs = {}
    for d in sorted(doc_ids):
        if lake.exists(layout.doc_key(d)):
            meta = load_doc(lake, d)
            docs[d] = {"title": meta.get("title"), "name": meta.get("name"), "source": meta.get("source"),
                       "scope": meta.get("scope", "public"), "passages": meta.get("passages"),
                       "source_uri": meta.get("source_uri"),
                       "format": (meta.get("parser") or "text@1").split("@")[0]}

    passage_doc: dict[str, str] = {}
    for p, _, doc in ds.triples((None, KL.partOf, None)):
        passage_doc[str(p)] = _short(str(doc), base + "doc/")

    # A name or type is public when a public document's graph states it: the graphs of one
    # document carry its scope (ks:scope on the document, or on each row of a structured table).
    gscope: dict[str, set] = defaultdict(set)
    for _, _, sc, g in ds.quads((None, KL.scope, None, None)):
        gscope[str(getattr(g, "identifier", g))].add(str(sc))

    def public_graph(g) -> bool:
        g = str(getattr(g, "identifier", g))
        scopes = set(gscope.get(g, ()))
        d = unquote(g.rsplit("/", 1)[-1]) if g.startswith(base + "graph/") else ""
        if d in docs:
            scopes.add(docs[d].get("scope", "public"))
        return scopes == {"public"}

    def said(s, p) -> tuple[set, set]:
        everywhere, public = set(), set()
        for _, _, v, g in ds.quads((s, p, None, None)):
            everywhere.add(v)
            if public_graph(g):
                public.add(v)
        return everywhere, public

    def most_specific(types):
        return [t for t in types if not any(t != u and spec.is_a(u, t) for u in types)]

    entities: dict[str, dict] = {}
    typed = set(ds.subjects(KL.mentionedIn, None))
    for s, _, t in ds.triples((None, RDF.type, None)):
        local = model.local_name(t)
        if str(t).startswith(spec.namespace) and local in spec.classes:
            typed.add(s)
    for s in typed:
        iri = str(s)
        ts, pts = said(s, RDF.type)
        types = sorted({model.local_name(t) for t in ts
                        if str(t).startswith(spec.namespace) and model.local_name(t) in spec.classes})
        if not types:
            continue
        ptypes = sorted({model.local_name(t) for t in pts} & set(types))
        labels, plabels = said(s, RDFS.label)
        aliases, paliases = said(s, SKOS.altLabel)
        pids = sorted({_short(str(p), base + "passage/") for p in ds.objects(s, KL.mentionedIn)})
        edocs = sorted({passage_doc.get(base + "passage/" + p, "") for p in pids} - {""})
        scope = str(ds.value(s, KL.scope) or "")
        if not scope:
            scope = "public" if any(docs.get(d, {}).get("scope") == "public" for d in edocs) else "private"
        entities[iri] = {"id": _short(iri, base), "type": most_specific(types)[0], "types": types,
                         "label": (sorted(map(str, plabels)) or sorted(map(str, labels)) or [iri.rsplit("/", 1)[-1]])[0],
                         "aliases": sorted(map(str, aliases)),
                         "attributes": [], "out": [], "in": [], "passages": pids, "docs": edocs,
                         "scope": scope}
        if scope == "public" and ptypes:
            entities[iri]["public"] = {"type": most_specific(ptypes)[0], "types": ptypes,
                                       "aliases": sorted(map(str, paliases))}

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

    # What a public caller may see of each entity's counts, and of the collection's: facts and
    # documents from public text only.
    def shown(row) -> bool:
        return any(passages.get(p, {}).get("scope") == "public" for p in row["passages"])
    pub_ents = {e["id"]: e for e in entities.values() if "public" in e}
    pub_props: Counter = Counter()
    for e in pub_ents.values():
        e["public"]["docs"] = sum(1 for d in e["docs"] if docs.get(d, {}).get("scope") == "public")
        e["public"]["links"] = sum(1 for r in e["out"] + e["in"] if shown(r))
        pub_props.update(r["p"] for r in e["attributes"] + e["out"] if shown(r))

    class_counts: Counter = Counter()
    pub_classes: Counter = Counter()
    for e in entities.values():
        for t in {a for t in e["types"] for a in spec.ancestors(t)}:
            class_counts[t] += 1
    for e in pub_ents.values():
        for t in {a for t in e["public"]["types"] for a in spec.ancestors(t)}:
            pub_classes[t] += 1
    reg = json.loads(lake.get(layout.CANDIDATE_REGISTER)) if lake.exists(layout.CANDIDATE_REGISTER) else {"terms": []}
    history = []
    for v in versions.published_versions(lake):
        m = versions.manifest(lake, v)
        history.append({"version": v, "kind": m["kind"], "base": m.get("base"), "published_at": m.get("published_at"),
                        "counts": m.get("counts"), "note": m.get("note"), "in_chain": v in chain})
    # What the data shows: how often a relation links one class to another, by the most specific
    # type of each end. The portal's ontology view draws the pairs the ontology does not declare.
    observed: Counter = Counter()
    pub_observed: Counter = Counter()
    type_of = {e["id"]: e["type"] for e in entities.values()}
    for e in entities.values():
        for row in e["out"]:
            if row["o"] in type_of:
                observed[(e["type"], row["p"], type_of[row["o"]])] += 1
    for e in pub_ents.values():
        for row in e["out"]:
            if row["o"] in pub_ents and shown(row):
                pub_observed[(e["public"]["type"], row["p"], pub_ents[row["o"]]["public"]["type"])] += 1
    # ontology.json is what /api/ontology serves to every caller: its counts are of what public
    # documents show. The counts over everything are in the summary, for private-scope callers.
    ontology = {
        "namespace": spec.namespace, "version": version, "label": spec.label,
        "classes": [{"name": c.local, "iri": c.iri, "label": c.label, "definition": c.definition, "synonyms": list(c.alt_labels),
                     "parents": list(c.parents), "count": pub_classes.get(c.local, 0)}
                    for c in sorted(spec.classes.values(), key=lambda t: t.local)],
        "relations": [{"name": p.local, "label": p.label, "definition": p.definition, "domain": list(p.domain),
                       "range": list(p.range), "count": pub_props.get(p.local, 0)}
                      for p in sorted(spec.relations.values(), key=lambda t: t.local)],
        "attributes": [{"name": p.local, "label": p.label, "definition": p.definition, "domain": list(p.domain),
                        "datatype": p.range[0] if p.range else "string", "count": pub_props.get(p.local, 0)}
                       for p in sorted(spec.attributes.values(), key=lambda t: t.local)],
        "observed": [{"domain": d, "p": p, "range": r, "count": n} for (d, p, r), n in sorted(pub_observed.items())],
    }
    private_ontology = {
        "classes": {c: n for c, n in sorted(class_counts.items())}, "properties": dict(sorted(prop_counts.items())),
        "observed": [{"domain": d, "p": p, "range": r, "count": n} for (d, p, r), n in sorted(observed.items())]}
    pterms = public_terms(lake, reg.get("version") or version, docs)
    profile = load_profile(lake)
    summary = {
        "profile": profile.to_dict(), "version": version, "chain": chain, "history": history,
        "sources": [{"name": s.name, "type": s.type, "scope": s.scope} for s in load_sources(lake)],
        "counts": {"documents": len(docs), "entities": len(entities), "facts": sum(prop_counts.values()),
                   "passages": len(passages), "silver_documents": sum(1 for _ in lake.list(layout.SILVER_DOCS + "/"))},
        "candidates": [scoped_candidate(t, docs, lake, pterms) for t in reg["terms"][:60]],
        "public": {"counts": {"documents": sum(1 for d in docs.values() if d.get("scope") == "public"),
                              "entities": sum(1 for e in entities.values() if e["scope"] == "public"),
                              "facts": sum(pub_props.values()),
                              "passages": sum(1 for p in passages.values() if p.get("scope") == "public")}},
        "ontology_counts": private_ontology,
        "built_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
    }
    for name, obj in (("summary", summary), ("ontology", ontology), ("entities", list(entities.values())),
                      ("passages", passages), ("docs", docs)):
        put_json(lake, layout.index_key(version, name), obj)
    log.info("projected %s: %d documents, %d entities, %d facts", version, len(docs), len(entities),
             sum(prop_counts.values()))
    return summary["counts"]
