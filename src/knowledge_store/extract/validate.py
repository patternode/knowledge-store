"""Checks on an extraction result, each producing a message the model can act on in a
repair turn, prefixed with the item it is about ("entities[2] ...") so salvage can drop
that item alone.

* shape: the lists and fields the schema requires, with vocabulary terms that exist;
* ontology: an attribute's or relation's domain and range allow the entity types;
* grounding: cited passages exist, an entity's name (or an alias) is in a cited passage,
  a value is in a cited passage as written;
* SHACL: the RDF conforms to the core provenance shapes plus the ontology's own shapes.

Candidates are checked for grounding but never cause a repair: a candidate whose evidence
is not in its passage is dropped, because a repair turn costs more than the candidate is worth.
"""

from __future__ import annotations

import datetime as dt
import re
from decimal import Decimal, InvalidOperation

from rdflib import Graph

from ..ontology.model import OntologySpec
from ..refine.chunk import Passage
from ..sparql_lock import PARSE_LOCK

SECTIONS = ("entities", "attributes", "relations")


def norm(s: str) -> str:
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-").replace(" ", " ")
    return " ".join(s.split()).lower()


def _numbers(text: str) -> set[str]:
    return {m.group().replace(",", "") for m in re.finditer(r"(?<![\d.])\d[\d,]*(?:\.\d+)?", text)}


def _value_stated(value: str, kind: str, texts: list[str]) -> bool:
    v = norm(value)
    if any(v in norm(t) for t in texts):
        return True
    if kind in ("decimal", "integer"):
        digits = v.replace(",", "").lstrip("+-$€£")
        nums = set().union(*(_numbers(t) for t in texts))
        return digits in nums or digits.rstrip("0").rstrip(".") in {n.rstrip("0").rstrip(".") for n in nums if "." in n}
    return False


def parse_value(value: str, kind: str):
    """The literal's Python value, or a ValueError naming what is wrong."""
    v = value.strip()
    if kind == "decimal":
        try:
            return Decimal(v.replace(",", "").lstrip("$€£").rstrip("%").strip())
        except InvalidOperation:
            raise ValueError(f"{value!r} is not a number") from None
    if kind == "integer":
        try:
            return int(v.replace(",", ""))
        except ValueError:
            raise ValueError(f"{value!r} is not a whole number") from None
    if kind == "date":
        for fmt in ("%Y-%m-%d", "%d %B %Y", "%B %d, %Y", "%d %b %Y", "%b %d, %Y", "%Y"):
            try:
                return dt.datetime.strptime(v, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"{value!r} is not a date (write it as YYYY-MM-DD or as the passage has it)")
    if kind == "boolean":
        if v.lower() in ("true", "yes"):
            return True
        if v.lower() in ("false", "no"):
            return False
        raise ValueError(f"{value!r} is not true or false")
    return v


def shape_errors(result, spec: OntologySpec, known: dict[str, str] | None = None) -> list[str]:
    """known: ref -> class of entities already held (delta runs)."""
    if not isinstance(result, dict):
        return ["the result must be an object"]
    errs: list[str] = []
    for sec in (*SECTIONS, "candidates"):
        if sec in result and not isinstance(result[sec], list):
            errs.append(f"{sec} must be a list")
    if errs:
        return errs
    refs: dict[str, str] = dict(known or {})
    for i, e in enumerate(result.get("entities") or []):
        where = f"entities[{i}]"
        if not isinstance(e, dict):
            errs.append(f"{where} must be an object")
            continue
        if not str(e.get("ref") or "").strip():
            errs.append(f"{where} has no ref")
        elif e["ref"] in refs:
            errs.append(f"{where} reuses ref {e['ref']!r}; refs must be unique")
        if e.get("type") not in spec.classes:
            errs.append(f"{where} type {e.get('type')!r} is not an entity type in the ontology")
        if not str(e.get("name") or "").strip():
            errs.append(f"{where} has no name")
        if not isinstance(e.get("passage_ids"), list) or not e["passage_ids"]:
            errs.append(f"{where} cites no passage")
        if e.get("ref") and e.get("type") in spec.classes:
            refs.setdefault(e["ref"], e["type"])
    for i, a in enumerate(result.get("attributes") or []):
        where = f"attributes[{i}]"
        if not isinstance(a, dict):
            errs.append(f"{where} must be an object")
            continue
        prop = spec.attributes.get(a.get("property"))
        if prop is None:
            errs.append(f"{where} property {a.get('property')!r} is not an attribute in the ontology")
            continue
        if a.get("entity") not in refs:
            errs.append(f"{where} names entity {a.get('entity')!r}, which is not declared")
            continue
        if not spec.allows(prop, refs[a["entity"]]):
            errs.append(f"{where} {prop.local} applies to {'|'.join(prop.domain)}, not {refs[a['entity']]}")
        try:
            parse_value(str(a.get("value", "")), prop.range[0] if prop.range else "string")
        except ValueError as e:
            errs.append(f"{where} {e}")
        if not isinstance(a.get("passage_ids"), list) or not a["passage_ids"]:
            errs.append(f"{where} cites no passage")
    for i, r in enumerate(result.get("relations") or []):
        where = f"relations[{i}]"
        if not isinstance(r, dict):
            errs.append(f"{where} must be an object")
            continue
        prop = spec.relations.get(r.get("predicate"))
        if prop is None:
            errs.append(f"{where} predicate {r.get('predicate')!r} is not a relation in the ontology")
            continue
        s, o = r.get("subject"), r.get("object")
        if s not in refs or o not in refs:
            errs.append(f"{where} subject {s!r} or object {o!r} is not declared")
            continue
        if not spec.allows(prop, refs[s], refs[o]):
            errs.append(f"{where} {prop.local} goes {'|'.join(prop.domain) or 'any'} -> "
                        f"{'|'.join(prop.range) or 'any'}, not {refs[s]} -> {refs[o]}")
        if not isinstance(r.get("passage_ids"), list) or not r["passage_ids"]:
            errs.append(f"{where} cites no passage")
    return errs


def grounding_errors(result: dict, spec: OntologySpec, passages: list[Passage]) -> list[str]:
    by_id = {p.passage_id: p for p in passages}
    errs: list[str] = []
    ents = {e["ref"]: e for e in result.get("entities") or []}

    def cited(item: dict, where: str) -> list[str] | None:
        missing = [pid for pid in item.get("passage_ids") or [] if pid not in by_id]
        if missing:
            errs.append(f"{where} cites passages that do not exist: {missing[:3]}")
            return None
        return [by_id[pid].text for pid in item["passage_ids"]]

    for i, e in enumerate(result.get("entities") or []):
        texts = cited(e, f"entities[{i}]")
        if texts is None:
            continue
        names = [e["name"], *(e.get("aliases") or [])]
        if not any(norm(n) in norm(t) for n in names if n.strip() for t in texts):
            errs.append(f"entities[{i}] name {e['name']!r} does not appear in the passages it cites")
    for i, a in enumerate(result.get("attributes") or []):
        texts = cited(a, f"attributes[{i}]")
        if texts is None:
            continue
        prop = spec.attributes[a["property"]]
        if not _value_stated(str(a["value"]), prop.range[0] if prop.range else "string", texts):
            errs.append(f"attributes[{i}] value {a['value']!r} is not stated in the passages it cites; "
                        "copy it as written")
    for i, r in enumerate(result.get("relations") or []):
        cited(r, f"relations[{i}]")
    _ = ents
    return errs


def clean_candidates(result: dict, passages: list[Passage]) -> tuple[list[dict], int]:
    """The candidates whose evidence is verbatim in a cited passage, and how many were dropped."""
    by_id = {p.passage_id: p.text for p in passages}
    kept, dropped = [], 0
    for c in result.get("candidates") or []:
        if not isinstance(c, dict) or c.get("kind") not in ("class", "relation", "attribute"):
            dropped += 1
            continue
        texts = [by_id[p] for p in c.get("passage_ids") or [] if p in by_id]
        ev = norm(str(c.get("evidence") or ""))
        if not texts or not ev or not any(ev in norm(t) for t in texts) or not str(c.get("term") or "").strip():
            dropped += 1
            continue
        kept.append(c)
    return kept, dropped


def shacl_errors(data: Graph, shapes: Graph, tbox: Graph) -> tuple[bool, list[str], str]:
    from pyshacl import validate
    with PARSE_LOCK:
        conforms, report_graph, report_text = validate(
            data, shacl_graph=shapes, ont_graph=tbox, inference="rdfs", abort_on_first=False,
            allow_warnings=True, advanced=True)
    if conforms:
        return True, [], report_text
    from rdflib import Namespace
    SH = Namespace("http://www.w3.org/ns/shacl#")
    msgs = []
    for r in report_graph.subjects(SH.resultSeverity, SH.Violation):
        focus = report_graph.value(r, SH.focusNode)
        msg = report_graph.value(r, SH.resultMessage)
        path = report_graph.value(r, SH.resultPath)
        msgs.append(f"{focus} {path or ''}: {msg}".strip())
    return False, sorted(msgs), report_text
