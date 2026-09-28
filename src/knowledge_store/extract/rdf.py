"""Turn an extraction result into ontology-typed RDF with provenance.

One named graph per (ontology version, document), so a document's facts at a version are
replaced atomically and a later version's delta sits beside them. IRIs are content-derived:

    entity     <data>/entity/<root class>/<slug of name>   the same name and root type across
                                                           documents is one node (naive entity
                                                           resolution: see the README's limits)
    assertion  <data>/assertion/<hash of s, p, o>          one reified statement per fact
    passage    <data>/passage/<passage id>
    document   <data>/doc/<doc id>
    run        <data>/run/<run id>
    graph      <data>/graph/<version>/<doc id>

<data> is the ontology namespace with "/id/" in place of its fragment, so two deployments
with different ontologies never mint the same IRIs.
"""

from __future__ import annotations

import hashlib
import re
from urllib.parse import quote

from rdflib import RDF, RDFS, XSD, Dataset, Graph, Literal, URIRef
from rdflib.namespace import SKOS

from ..ontology.model import DATATYPES, KL, OntologySpec
from ..refine.chunk import Passage
from .validate import parse_value


def data_base(spec: OntologySpec) -> str:
    return spec.namespace.rstrip("#/") + "/id/"


def slug(name: str) -> str:
    s = re.sub(r"[^0-9a-z]+", "-", name.lower()).strip("-")
    return s[:80] or hashlib.sha1(name.encode()).hexdigest()[:12]


class Iris:
    def __init__(self, spec: OntologySpec):
        self.spec = spec
        self.base = data_base(spec)

    def _iri(self, *parts: str) -> URIRef:
        return URIRef(self.base + "/".join(quote(str(p), safe="-_.") for p in parts))

    def entity(self, cls: str, name: str) -> URIRef:
        return self._iri("entity", self.spec.root(cls), slug(name))

    def passage(self, pid: str) -> URIRef:
        return self._iri("passage", pid)

    def doc(self, doc_id: str) -> URIRef:
        return self._iri("doc", doc_id)

    def run(self, run_id: str) -> URIRef:
        return self._iri("run", run_id)

    def graph(self, version: str, doc_id: str) -> URIRef:
        return self._iri("graph", version, doc_id)

    def assertion(self, s, p, o) -> URIRef:
        h = hashlib.sha1(f"{s}|{p}|{o}".encode()).hexdigest()[:20]
        return self._iri("assertion", h)


def build_graph(result: dict, *, spec: OntologySpec, doc: dict, passages: list[Passage], run: dict,
                known: dict[str, dict] | None = None) -> tuple[Graph, dict[str, str]]:
    """The document's graph, and node IRI -> item label ("entities[2]") for mapping SHACL
    messages back to the items that produced them. known: ref -> {"iri", "type"} of entities
    already held for this document (delta runs)."""
    ids = Iris(spec)
    g = Graph()
    g.bind("ks", KL)
    g.bind("skos", SKOS)
    g.bind("o", spec.namespace)
    where: dict[str, str] = {}

    d = ids.doc(doc["doc_id"])
    g.add((d, RDF.type, KL.Document))
    if doc.get("title"):
        g.add((d, RDFS.label, Literal(doc["title"])))
    g.add((d, KL.source, Literal(doc.get("source", ""))))
    g.add((d, KL.scope, Literal(doc.get("scope", "public"))))
    g.add((d, KL.contentHash, Literal(doc["doc_id"])))

    r = ids.run(run["run_id"])
    g.add((r, RDF.type, KL.ExtractionRun))
    g.add((r, KL.modelId, Literal(run["model_id"])))
    g.add((r, KL.promptVersion, Literal(run["prompt_version"])))
    g.add((r, KL.ontologyVersion, Literal(run["ontology_version"])))
    if run.get("delta"):
        g.add((r, KL.delta, Literal(True)))

    by_id = {p.passage_id: p for p in passages}
    used: set[str] = set()

    def cite(item: dict) -> list[URIRef]:
        out = []
        for pid in item.get("passage_ids") or []:
            if pid in by_id:
                used.add(pid)
                out.append(ids.passage(pid))
        return out

    ents: dict[str, URIRef] = {k: URIRef(v["iri"]) for k, v in (known or {}).items()}
    for i, e in enumerate(result.get("entities") or []):
        node = ids.entity(e["type"], e["name"])
        ents[e["ref"]] = node
        where[str(node)] = f"entities[{i}]"
        g.add((node, RDF.type, spec.iri_of(e["type"])))
        g.add((node, RDFS.label, Literal(e["name"].strip())))
        for alias in e.get("aliases") or []:
            if alias.strip() and alias.strip() != e["name"].strip():
                g.add((node, SKOS.altLabel, Literal(alias.strip())))
        for p in cite(e):
            g.add((node, KL.mentionedIn, p))

    def reify(s, p, o, item: dict, label: str) -> None:
        a = ids.assertion(s, p, o)
        where[str(a)] = label
        g.add((s, p, o))
        g.add((a, RDF.type, KL.Assertion))
        g.add((a, RDF.subject, s))
        g.add((a, RDF.predicate, p))
        g.add((a, RDF.object, o))
        g.add((a, KL.extractedBy, r))
        for c in cite(item):
            g.add((a, KL.extractedFrom, c))

    for i, a in enumerate(result.get("attributes") or []):
        prop = spec.attributes[a["property"]]
        kind = prop.range[0] if prop.range else "string"
        value = parse_value(str(a["value"]), kind)
        lit = Literal(value, datatype=DATATYPES[kind]) if kind != "string" else Literal(value)
        reify(ents[a["entity"]], URIRef(prop.iri), lit, a, f"attributes[{i}]")

    for i, rel in enumerate(result.get("relations") or []):
        prop = spec.relations[rel["predicate"]]
        reify(ents[rel["subject"]], URIRef(prop.iri), ents[rel["object"]], rel, f"relations[{i}]")

    for pid in used:
        p = by_id[pid]
        pi = ids.passage(pid)
        g.add((pi, RDF.type, KL.Passage))
        g.add((pi, KL.partOf, d))
        g.add((pi, KL.seq, Literal(p.seq, datatype=XSD.integer)))
        g.add((pi, KL.contentHash, Literal(p.content_hash)))
    return g, where


def label_messages(messages: list[str], where: dict[str, str]) -> list[str]:
    out = []
    for m in messages:
        hit = next((label for node, label in where.items() if m.startswith(node)), None)
        out.append(f"{hit} {m}" if hit else m)
    return out


def to_nquads(g: Graph, graph_iri: URIRef) -> bytes:
    ds = Dataset()
    ctx = ds.graph(graph_iri)
    for t in g:
        ctx.add(t)
    return ds.serialize(format="nquads", encoding="utf-8")
