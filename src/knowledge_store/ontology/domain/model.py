"""Load a domain ontology (OWL in Turtle) into the spec every other step derives from.

What the lab reads from the file:

    owl:Class                 with rdfs:label, skos:altLabel (synonyms), rdfs:comment or
                              skos:definition, rdfs:subClassOf (single or multiple parents)
    owl:ObjectProperty        with rdfs:domain and rdfs:range naming classes: a relation
    owl:DatatypeProperty      with rdfs:domain and an xsd rdfs:range: an attribute
    owl:Ontology              with owl:versionInfo, owl:versionIRI, owl:priorVersion

Terms are named by their local name (the part after # or the last /), which must be unique
across classes and properties: it is what the model writes in the tool call. Only terms in
the ontology's own namespace are extracted into; imported or aligned terms are ignored.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

from rdflib import OWL, RDF, RDFS, XSD, Graph, Literal, Namespace, URIRef
from rdflib.namespace import SKOS

KL = Namespace("https://w3id.org/knowledge-store/core#")
PACKAGE_DIR = Path(__file__).resolve().parent
CORE_TTL = PACKAGE_DIR / "core.ttl"
CORE_SHAPES = PACKAGE_DIR / "core-shapes.ttl"

# The value kinds an attribute can take, and the xsd datatypes they map to.
DATATYPES = {"string": XSD.string, "decimal": XSD.decimal, "integer": XSD.integer,
             "date": XSD.date, "boolean": XSD.boolean, "anyURI": XSD.anyURI}
_XSD_KIND = {v: k for k, v in DATATYPES.items()} | {XSD.double: "decimal", XSD.float: "decimal",
                                                     XSD.dateTime: "date", XSD.int: "integer"}


def local_name(iri: str) -> str:
    s = str(iri)
    return s.rsplit("#", 1)[1] if "#" in s else s.rstrip("/").rsplit("/", 1)[-1]


@dataclass(frozen=True)
class Term:
    iri: str
    local: str
    label: str
    alt_labels: tuple[str, ...] = ()
    definition: str = ""

    def names(self) -> tuple[str, ...]:
        return (self.label, self.local, *self.alt_labels)


@dataclass(frozen=True)
class ClassTerm(Term):
    parents: tuple[str, ...] = ()           # local names of in-namespace superclasses


@dataclass(frozen=True)
class PropertyTerm(Term):
    domain: tuple[str, ...] = ()            # local class names; empty means any class
    range: tuple[str, ...] = ()             # class locals for a relation; one kind for an attribute
    kind: str = "relation"                  # relation or attribute


@dataclass
class OntologySpec:
    namespace: str
    version: str
    iri: str = ""
    version_iri: str = ""
    prior_version: str = ""
    label: str = ""
    comment: str = ""
    classes: dict[str, ClassTerm] = field(default_factory=dict)
    relations: dict[str, PropertyTerm] = field(default_factory=dict)
    attributes: dict[str, PropertyTerm] = field(default_factory=dict)
    graph: Graph | None = None

    # -- hierarchy -----------------------------------------------------------------------

    def ancestors(self, cls: str) -> set[str]:
        """cls and every in-namespace superclass of it."""
        seen, todo = set(), [cls]
        while todo:
            c = todo.pop()
            if c in seen or c not in self.classes:
                continue
            seen.add(c)
            todo.extend(self.classes[c].parents)
        return seen

    def is_a(self, cls: str, target: str) -> bool:
        return target in self.ancestors(cls)

    def root(self, cls: str) -> str:
        """The top of cls's first parent chain. Entity IRIs are keyed by it, so an entity
        retyped to a subclass in a later version keeps its IRI."""
        c, seen = cls, set()
        while c in self.classes and self.classes[c].parents and c not in seen:
            seen.add(c)
            c = sorted(self.classes[c].parents)[0]
        return c

    def allows(self, prop: PropertyTerm, subject_cls: str, object_cls: str | None = None) -> bool:
        if prop.domain and not any(self.is_a(subject_cls, d) for d in prop.domain):
            return False
        if object_cls is not None and prop.kind == "relation" and prop.range:
            return any(self.is_a(object_cls, r) for r in prop.range)
        return True

    def term(self, local: str) -> Term | None:
        return self.classes.get(local) or self.relations.get(local) or self.attributes.get(local)

    def iri_of(self, local: str) -> URIRef:
        t = self.term(local)
        return URIRef(t.iri if t else self.namespace + local)

    @cached_property
    def synonym_index(self) -> dict[str, str]:
        """lower-cased label, local name or synonym -> local name, across every term."""
        idx: dict[str, str] = {}
        for t in (*self.classes.values(), *self.relations.values(), *self.attributes.values()):
            for n in t.names():
                idx.setdefault(normalise(n), t.local)
        return idx

    def is_empty(self) -> bool:
        return not self.classes

    # -- prompt ---------------------------------------------------------------------------

    def vocabulary_prompt(self, only: set[str] | None = None) -> str:
        """The ontology as the extraction prompt's vocabulary block: type definitions with
        their synonyms (give the model the types it must extract into). With only, just those
        terms (a delta run), plus the classes they reference so domains and ranges read."""
        def keep(t: Term) -> bool:
            return only is None or t.local in only

        def line(t: Term, extra: str = "") -> str:
            syn = f" (also: {', '.join(t.alt_labels)})" if t.alt_labels else ""
            d = f": {t.definition}" if t.definition else ""
            return f"- {t.local}{extra}: {t.label}{syn}{d}"

        needed = set(only or ())
        for p in (*self.relations.values(), *self.attributes.values()):
            if keep(p):
                needed |= set(p.domain) | (set(p.range) if p.kind == "relation" else set())
        parts = ["## Entity types (use the name on the left as `type`)"]
        for c in sorted(self.classes.values(), key=lambda t: t.local):
            if only is None or c.local in needed:
                sub = f" [a kind of {', '.join(sorted(c.parents))}]" if c.parents else ""
                parts.append(line(c, sub))
        rels = [p for p in self.relations.values() if keep(p)]
        if rels:
            parts += ["", "## Relations (use as `predicate`, subject -> object)"]
            for p in sorted(rels, key=lambda t: t.local):
                sig = f" [{'|'.join(p.domain) or 'any'} -> {'|'.join(p.range) or 'any'}]"
                parts.append(line(p, sig))
        attrs = [p for p in self.attributes.values() if keep(p)]
        if attrs:
            parts += ["", "## Attributes (use as `property`, with a literal value)"]
            for p in sorted(attrs, key=lambda t: t.local):
                sig = f" [{'|'.join(p.domain) or 'any'}: {p.range[0] if p.range else 'string'}]"
                parts.append(line(p, sig))
        return "\n".join(parts)


def normalise(s: str) -> str:
    """A name as a comparison key: case, spacing, punctuation and camelCase folded."""
    import re
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", s)
    return " ".join(re.sub(r"[^0-9a-zA-Z]+", " ", s).lower().split())


def _text(g: Graph, s, *preds) -> str:
    for p in preds:
        vals = [o for o in g.objects(s, p) if isinstance(o, Literal)]
        en = [o for o in vals if (o.language or "en").startswith("en")]
        if en or vals:
            return str((en or vals)[0])
    return ""


def _namespace(g: Graph, onto: URIRef | None) -> str:
    """The ontology's own namespace: its IRI plus # (or / if it ends in one), else the
    namespace most of its classes share."""
    if onto is not None:
        s = str(onto)
        return s if s.endswith(("#", "/")) else s + "#"
    counts: dict[str, int] = {}
    for c in g.subjects(RDF.type, OWL.Class):
        if isinstance(c, URIRef):
            s = str(c)
            ns = s.rsplit("#", 1)[0] + "#" if "#" in s else s.rsplit("/", 1)[0] + "/"
            counts[ns] = counts.get(ns, 0) + 1
    return max(counts, key=counts.get) if counts else ""


def from_graph(g: Graph) -> OntologySpec:
    onto = next((s for s in g.subjects(RDF.type, OWL.Ontology) if isinstance(s, URIRef)), None)
    ns = _namespace(g, onto)
    spec = OntologySpec(
        namespace=ns,
        version=_text(g, onto, OWL.versionInfo) if onto is not None else "",
        iri=str(onto or ""),
        version_iri=str(g.value(onto, OWL.versionIRI) or "") if onto is not None else "",
        prior_version=str(g.value(onto, OWL.priorVersion) or "") if onto is not None else "",
        label=_text(g, onto, RDFS.label) if onto is not None else "",
        comment=_text(g, onto, RDFS.comment) if onto is not None else "",
        graph=g,
    )

    def mine(s) -> bool:
        return isinstance(s, URIRef) and str(s).startswith(ns) and not g.value(s, OWL.deprecated)

    def base(s) -> dict:
        return {"iri": str(s), "local": local_name(s),
                "label": _text(g, s, RDFS.label, SKOS.prefLabel) or local_name(s),
                "alt_labels": tuple(sorted({str(o) for o in g.objects(s, SKOS.altLabel)})),
                "definition": _text(g, s, SKOS.definition, RDFS.comment)}

    for s in set(g.subjects(RDF.type, OWL.Class)):
        if mine(s):
            parents = tuple(sorted(local_name(o) for o in g.objects(s, RDFS.subClassOf) if mine(o)))
            spec.classes[local_name(s)] = ClassTerm(**base(s), parents=parents)
    for s in set(g.subjects(RDF.type, OWL.ObjectProperty)):
        if mine(s):
            spec.relations[local_name(s)] = PropertyTerm(
                **base(s), kind="relation",
                domain=tuple(sorted(local_name(o) for o in g.objects(s, RDFS.domain) if mine(o))),
                range=tuple(sorted(local_name(o) for o in g.objects(s, RDFS.range) if mine(o))))
    for s in set(g.subjects(RDF.type, OWL.DatatypeProperty)):
        if mine(s):
            rng = g.value(s, RDFS.range)
            spec.attributes[local_name(s)] = PropertyTerm(
                **base(s), kind="attribute",
                domain=tuple(sorted(local_name(o) for o in g.objects(s, RDFS.domain) if mine(o))),
                range=(_XSD_KIND.get(rng, "string"),))
    clash = set(spec.classes) & (set(spec.relations) | set(spec.attributes)) | set(spec.relations) & set(spec.attributes)
    if clash:
        raise ValueError(f"ontology local names must be unique across classes and properties: {sorted(clash)}")
    return spec


def load(path: str | Path | None = None, *, data: bytes | str | None = None) -> OntologySpec:
    g = Graph()
    if data is not None:
        g.parse(data=data, format="turtle")
    else:
        g.parse(str(path), format="turtle")
    return from_graph(g)


def empty(namespace: str = "https://example.org/ontology/lab#") -> OntologySpec:
    return OntologySpec(namespace=namespace, version="0.0.0", graph=Graph())
