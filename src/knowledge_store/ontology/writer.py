"""Write an ontology definition (from discovery or a revision proposal) as Turtle and SHACL.

The definition is plain data:

    {"classes":    [{"name", "label", "definition", "synonyms", "parent"}],
     "relations":  [{"name", "label", "definition", "synonyms", "domain", "range"}],
     "attributes": [{"name", "label", "definition", "synonyms", "domain", "datatype"}]}

The output is meant for a person to edit, so it is written by hand rather than serialised by
rdflib: one block per term, in a stable order, with the evidence counts as comments.
"""

from __future__ import annotations

import datetime as dt
import re

from .model import DATATYPES, OntologySpec

XSD_NAME = {k: f"xsd:{k}" for k in DATATYPES}


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


def normalise_definition(defn: dict) -> dict:
    """Canonical local names, and references between terms resolved to them. Terms that
    reference an unknown class lose that reference rather than inventing a class."""
    classes = {}
    for c in defn.get("classes") or []:
        n = class_name(c["name"])
        if n and n not in classes:
            classes[n] = {**c, "name": n}
    for c in classes.values():
        p = class_name(c["parent"]) if c.get("parent") else None
        c["parent"] = p if p in classes and p != c["name"] else None
    rels, attrs = {}, {}
    for r in defn.get("relations") or []:
        n = property_name(r["name"])
        dom = [class_name(x) for x in _as_list(r.get("domain")) if class_name(x) in classes]
        rng = [class_name(x) for x in _as_list(r.get("range")) if class_name(x) in classes]
        if n and n not in rels and n not in classes:
            rels[n] = {**r, "name": n, "domain": dom, "range": rng}
    for a in defn.get("attributes") or []:
        n = property_name(a["name"])
        dom = [class_name(x) for x in _as_list(a.get("domain")) if class_name(x) in classes]
        dtp = a.get("datatype") if a.get("datatype") in DATATYPES else "string"
        if n and n not in attrs and n not in rels and n not in classes:
            attrs[n] = {**a, "name": n, "domain": dom, "datatype": dtp}
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
        "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .",
        "",
        f"<{onto}> a owl:Ontology ;",
        f"    rdfs:label {_lit(label)} ;",
        f"    owl:versionInfo \"{version}\" ;",
        f"    owl:versionIRI <{onto}/{version}> ;",
    ]
    if prior is not None and prior.version:
        out.append(f"    owl:priorVersion <{onto}/{prior.version}> ;")
    out.append(f"    rdfs:comment {_lit(comment or f'Generated {dt.date.today().isoformat()}; curate before publishing.')} .")
    out += ["", "# " + "=" * 70, "# Classes", "# " + "=" * 70, ""]
    for c in sorted(d["classes"], key=lambda x: x["name"]):
        extra = [f"rdfs:subClassOf o:{c['parent']}"] if c.get("parent") else []
        note = f"seen in {ev[c['name']]} documents" if c["name"] in ev else ""
        out += [_block(f"o:{c['name']}", "owl:Class", c, extra, note), ""]
    if d["relations"]:
        out += ["# " + "=" * 70, "# Relations", "# " + "=" * 70, ""]
    for r in sorted(d["relations"], key=lambda x: x["name"]):
        extra = [f"rdfs:domain o:{x}" for x in r["domain"]] + [f"rdfs:range o:{x}" for x in r["range"]]
        note = f"seen in {ev[r['name']]} documents" if r["name"] in ev else ""
        out += [_block(f"o:{r['name']}", "owl:ObjectProperty", r, extra, note), ""]
    if d["attributes"]:
        out += ["# " + "=" * 70, "# Attributes", "# " + "=" * 70, ""]
    for a in sorted(d["attributes"], key=lambda x: x["name"]):
        extra = [f"rdfs:domain o:{x}" for x in a["domain"]] + [f"rdfs:range {XSD_NAME[a['datatype']]}"]
        note = f"seen in {ev[a['name']]} documents" if a["name"] in ev else ""
        out += [_block(f"o:{a['name']}", "owl:DatatypeProperty", a, extra, note), ""]
    return "\n".join(out)


def _merge(prior: OntologySpec, d: dict) -> dict:
    classes = {c.local: {"name": c.local, "label": c.label, "definition": c.definition,
                         "synonyms": list(c.alt_labels), "parent": (sorted(c.parents) or [None])[0]}
               for c in prior.classes.values()}
    rels = {p.local: {"name": p.local, "label": p.label, "definition": p.definition,
                      "synonyms": list(p.alt_labels), "domain": list(p.domain), "range": list(p.range)}
            for p in prior.relations.values()}
    attrs = {p.local: {"name": p.local, "label": p.label, "definition": p.definition,
                       "synonyms": list(p.alt_labels), "domain": list(p.domain),
                       "datatype": p.range[0] if p.range else "string"}
             for p in prior.attributes.values()}
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
    out = [f"@prefix o:  <{ns}> .", "@prefix sh: <http://www.w3.org/ns/shacl#> .",
           "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .", "",
           "# Generated from the ontology's domains and ranges. Edit freely; it is published with the version.", ""]
    for p in sorted(spec.relations.values(), key=lambda t: t.local):
        if len(p.range) == 1:
            out += [f"o:{p.local}RangeShape a sh:NodeShape ;", f"    sh:targetSubjectsOf o:{p.local} ;",
                    f"    sh:property [ sh:path o:{p.local} ; sh:class o:{p.range[0]} ;",
                    f"                  sh:message \"{p.local} must point at a {p.range[0]}\" ] .", ""]
    for p in sorted(spec.attributes.values(), key=lambda t: t.local):
        kind = p.range[0] if p.range else "string"
        out += [f"o:{p.local}DatatypeShape a sh:NodeShape ;", f"    sh:targetSubjectsOf o:{p.local} ;",
                f"    sh:property [ sh:path o:{p.local} ; sh:datatype {XSD_NAME[kind]} ;",
                f"                  sh:message \"{p.local} must be a {kind}\" ] .", ""]
    return "\n".join(out)
