"""Write an ontology definition (from discovery or a revision proposal) as Turtle and SHACL.

The definition is plain data:

    {"classes":    [{"name", "label", "definition", "synonyms", "parent"}],
     "relations":  [{"name", "label", "definition", "synonyms", "domain", "range"}],
     "attributes": [{"name", "label", "definition", "synonyms", "domain", "datatype", "unit"}]}

The output is meant for a person to edit, so it is written by hand rather than serialised by
rdflib: one block per term, in a stable order, with the evidence counts as comments.
"""

from __future__ import annotations

import datetime as dt
import re

from knowledge_store.ontology.domain.model import DATATYPES, FOUNDATION_CLASSES, MEASURES_NS, OntologySpec

def datatype_name(kind: str) -> str:
    """The prefixed name of a value kind. An interval is a values datatype, not an XML Schema one."""
    if kind == "interval":
        return "kv:interval"
    return f"xsd:{kind}"


def class_name(s: str) -> str:
    """UpperCamelCase local name for a class."""
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", s)
    words = re.sub(r"[^0-9A-Za-z]+", " ", words).split()
    out = "".join(w[:1].upper() + w[1:] for w in words)
    return out if out and out[0].isalpha() else "T" + out


def property_name(s: str) -> str:
    """lowerCamelCase local name for a property."""
    c = class_name(s)
    return c[:1].lower() + c[1:]


def _unit(unit: str) -> str:
    if unit.startswith(("http://", "https://")):
        return f"<{unit}>"
    return '"' + unit.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _lit(s: str) -> str:
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"@en'


def _block(subject: str, kind: str, t: dict, extra: list[str], note: str = "") -> str:
    lines = [f"{subject} a {kind} ;", f"    rdfs:label {_lit(t.get('label') or t['name'])} ;"]
    syns = sorted({s for s in t.get("synonyms") or [] if s and s != t.get("label")})
    if syns:
        lines.append("    skos:altLabel " + ", ".join(_lit(s) for s in syns) + " ;")
    if t.get("definition"):
        lines.append(f"    skos:definition {_lit(t['definition'])} ;")
    lines += [f"    {e} ;" for e in extra]
    lines[-1] = lines[-1][:-2] + " ."
    head = f"# {note}\n" if note else ""
    return head + "\n".join(lines)


def _known(classes: dict, name: str) -> bool:
    """A class this definition declares, or one of the four measures classes it may use."""
    return name in classes or name in FOUNDATION_CLASSES


def _class_ref(name: str) -> str:
    return f"km:{name}" if name in FOUNDATION_CLASSES else f"o:{name}"


def _uses_foundation(d: dict) -> bool:
    names = FOUNDATION_CLASSES
    if any(c.get("parent") in names for c in d["classes"]):
        return True
    for group, fields in ((d["relations"], ("domain", "range")), (d["attributes"], ("domain",))):
        for term in group:
            if any(n in names for field in fields for n in term.get(field) or []):
                return True
    return False


def normalise_definition(defn: dict) -> dict:
    """Canonical local names, and references between terms resolved to them. Terms that
    reference an unknown class lose that reference rather than inventing a class.
    Metric, Quantity, Instant and Period are already defined: a reference to one is kept,
    and a class declared under that name is dropped."""
    classes = {}
    for c in defn.get("classes") or []:
        n = class_name(c["name"])
        if n and n not in classes and n not in FOUNDATION_CLASSES:
            classes[n] = {**c, "name": n}
    for c in classes.values():
        p = class_name(c["parent"]) if c.get("parent") else None
        c["parent"] = p if _known(classes, p or "") and p != c["name"] else None
    rels, attrs = {}, {}
    for r in defn.get("relations") or []:
        n = property_name(r["name"])
        dom = [class_name(x) for x in _as_list(r.get("domain")) if _known(classes, class_name(x))]
        rng = [class_name(x) for x in _as_list(r.get("range")) if _known(classes, class_name(x))]
        if n and n not in rels and n not in classes and n not in FOUNDATION_CLASSES:
            rels[n] = {**r, "name": n, "domain": dom, "range": rng}
    for a in defn.get("attributes") or []:
        n = property_name(a["name"])
        dom = [class_name(x) for x in _as_list(a.get("domain")) if _known(classes, class_name(x))]
        dtp = a.get("datatype") if a.get("datatype") in DATATYPES else "string"
        unit = (a.get("unit") or "") if dtp in ("decimal", "integer") else ""
        if n and n not in attrs and n not in rels and n not in classes and n not in FOUNDATION_CLASSES:
            attrs[n] = {**a, "name": n, "domain": dom, "datatype": dtp, "unit": unit}
    return {"classes": list(classes.values()), "relations": list(rels.values()), "attributes": list(attrs.values())}


def _as_list(v) -> list[str]:
    if not v:
        return []
    return [v] if isinstance(v, str) else [x for x in v if x]


def ontology_ttl(defn: dict, *, namespace: str, version: str, label: str, comment: str = "",
                 prior: OntologySpec | None = None, evidence: dict[str, int] | None = None) -> str:
    """Turtle for the definition. With prior, its terms are kept (merged by local name, the
    definition's synonyms added) so a revision is written as the whole next version."""
    d = normalise_definition(defn)
    if prior is not None:
        d = _merge(prior, d)
    ev = evidence or {}
    onto = namespace.rstrip("#/")
    out = [
        f"@prefix o:    <{namespace}> .",
        "@prefix owl:  <http://www.w3.org/2002/07/owl#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .",
        "@prefix kv:   <https://w3id.org/knowledge-store/values#> .",
        "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .",
    ]
    if _uses_foundation(d):
        out.append("@prefix km:   <https://w3id.org/knowledge-store/measures#> .")
    out += [
        "",
        f"<{onto}> a owl:Ontology ;",
        f"    rdfs:label {_lit(label)} ;",
        f"    owl:versionInfo \"{version}\" ;",
        f"    owl:versionIRI <{onto}/{version}> ;",
    ]
    if _uses_foundation(d):
        out.append("    owl:imports <https://w3id.org/knowledge-store/measures> ;")
    if prior is not None and prior.version:
        out.append(f"    owl:priorVersion <{onto}/{prior.version}> ;")
    out.append(f"    rdfs:comment {_lit(comment or f'Generated {dt.date.today().isoformat()}; curate before publishing.')} .")
    out += ["", "# " + "=" * 70, "# Classes", "# " + "=" * 70, ""]
    for c in sorted(d["classes"], key=lambda x: x["name"]):
        extra = [f"rdfs:subClassOf {_class_ref(c['parent'])}"] if c.get("parent") else []
        note = f"seen in {ev[c['name']]} documents" if c["name"] in ev else ""
        out += [_block(f"o:{c['name']}", "owl:Class", c, extra, note), ""]
    if d["relations"]:
        out += ["# " + "=" * 70, "# Relations", "# " + "=" * 70, ""]
    for r in sorted(d["relations"], key=lambda x: x["name"]):
        extra = [f"rdfs:domain {_class_ref(x)}" for x in r["domain"]] + [f"rdfs:range {_class_ref(x)}" for x in r["range"]]
        note = f"seen in {ev[r['name']]} documents" if r["name"] in ev else ""
        out += [_block(f"o:{r['name']}", "owl:ObjectProperty", r, extra, note), ""]
    if d["attributes"]:
        out += ["# " + "=" * 70, "# Attributes", "# " + "=" * 70, ""]
    for a in sorted(d["attributes"], key=lambda x: x["name"]):
        extra = [f"rdfs:domain {_class_ref(x)}" for x in a["domain"]] + [f"rdfs:range {datatype_name(a['datatype'])}"]
        if a.get("unit"):
            extra.append(f"kv:unit {_unit(a['unit'])}")
        note = f"seen in {ev[a['name']]} documents" if a["name"] in ev else ""
        out += [_block(f"o:{a['name']}", "owl:DatatypeProperty", a, extra, note), ""]
    return "\n".join(out)


def _own(iri: str) -> bool:
    return not iri.startswith(MEASURES_NS)


def _merge(prior: OntologySpec, d: dict) -> dict:
    # The measures classes come back through the import. Copying them would declare them again.
    classes = {c.local: {"name": c.local, "label": c.label, "definition": c.definition,
                         "synonyms": list(c.alt_labels), "parent": (sorted(c.parents) or [None])[0]}
               for c in prior.classes.values() if _own(c.iri)}
    rels = {p.local: {"name": p.local, "label": p.label, "definition": p.definition,
                      "synonyms": list(p.alt_labels), "domain": list(p.domain), "range": list(p.range)}
            for p in prior.relations.values() if _own(p.iri)}
    attrs = {p.local: {"name": p.local, "label": p.label, "definition": p.definition,
                       "synonyms": list(p.alt_labels), "domain": list(p.domain),
                       "datatype": p.range[0] if p.range else "string", "unit": p.unit}
             for p in prior.attributes.values() if _own(p.iri)}
    for src, dst in ((d["classes"], classes), (d["relations"], rels), (d["attributes"], attrs)):
        for t in src:
            if t["name"] in dst:  # an existing term: the proposal may only add synonyms
                dst[t["name"]]["synonyms"] = sorted(set(dst[t["name"]]["synonyms"]) | set(t.get("synonyms") or []))
            else:
                dst[t["name"]] = t
    return normalise_definition({"classes": list(classes.values()), "relations": list(rels.values()),
                                 "attributes": list(attrs.values())})


def shapes_ttl(spec: OntologySpec) -> str:
    """SHACL generated from the ontology's signatures: a relation's object must be of its range,
    an attribute's value of its datatype. Written out so a curator can tighten it by hand."""
    ns = spec.namespace

    def shape_class(local: str) -> str:
        term = spec.classes.get(local)
        if term is not None and term.iri.startswith(MEASURES_NS):
            return f"km:{local}"
        return f"o:{local}"

    relations = [p for p in spec.relations.values() if _own(p.iri)]
    attributes = [p for p in spec.attributes.values() if _own(p.iri)]
    out = [f"@prefix o:  <{ns}> .", "@prefix sh: <http://www.w3.org/ns/shacl#> .",
           "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
           "@prefix kv: <https://w3id.org/knowledge-store/values#> ."]
    if any(shape_class(local).startswith("km:") for p in relations for local in p.range):
        out.append("@prefix km: <https://w3id.org/knowledge-store/measures#> .")
    out += ["", "# Generated from the ontology's domains and ranges. Edit freely; it is published with the version.", ""]
    for p in sorted(relations, key=lambda t: t.local):
        if len(p.range) == 1:
            out += [f"o:{p.local}RangeShape a sh:NodeShape ;", f"    sh:targetSubjectsOf o:{p.local} ;",
                    f"    sh:property [ sh:path o:{p.local} ; sh:class {shape_class(p.range[0])} ;",
                    f"                  sh:message \"{p.local} must point at a {p.range[0]}\" ] .", ""]
    for p in sorted(attributes, key=lambda t: t.local):
        kind = p.range[0] if p.range else "string"
        out += [f"o:{p.local}DatatypeShape a sh:NodeShape ;", f"    sh:targetSubjectsOf o:{p.local} ;",
                f"    sh:property [ sh:path o:{p.local} ; sh:datatype {datatype_name(kind)} ;",
                f"                  sh:message \"{p.local} must be a {kind}\" ] .", ""]
    return "\n".join(out)
