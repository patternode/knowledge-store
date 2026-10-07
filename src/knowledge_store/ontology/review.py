"""Review: a second look at a discovered ontology before anyone curates or publishes it.

Consolidation (discover.py, step 3) designs the ontology in one call, and its drafts tend to be
flat, with near-duplicate terms and loose domains. Review gives the draft, with how many sampled
documents supported each term, to one more call that returns edits, never a new ontology:

    set_parent     put a class under another (null to make it a root)
    merge          fold a term into another of the same kind; its names become synonyms
    drop           remove a term that is noise or out of scope
    set_domain     the class a relation or attribute belongs to
    set_range      the class a relation points to
    set_datatype   an attribute's datatype

Each edit carries a reason. Edits are applied here, deterministically, and checked as they go: a
parent that would make a cycle, a term that does not exist or a datatype the model does not know
is skipped and reported, never guessed at. The draft's report lists what was applied and what was
skipped, so the person who curates it can see, and undo, every change review made.
"""

from __future__ import annotations

import copy
import json
import logging

from ..config import Profile
from . import model

log = logging.getLogger("review")

REVIEW_TOOL = "review_ontology"
PROMPT_VERSION = "kl-review-v1"
OPS = ("set_parent", "merge", "drop", "set_domain", "set_range", "set_datatype")
KINDS = ("classes", "relations", "attributes")

REVIEW_SYSTEM = """You are reviewing a draft ontology that was discovered from a sample of a document
collection, before a person curates it.

{profile}

You get the draft's classes (with parents), relations (domain -> range) and attributes (domain, datatype),
each with a definition and the number of sampled documents that supported it. Return edits that make it a
better ontology for answering questions about this collection:
- Give the hierarchy depth where one class is genuinely a kind of another (set_parent). Drafts are usually
  too flat. Do not invent new classes; only arrange the ones there.
- Merge terms that mean the same thing (merge), keeping the clearer one.
- Drop terms that are noise, one-off phrases or out of scope for the collection (drop).
- Fix domains, ranges and datatypes that are wrong or too narrow (set_domain, set_range, set_datatype).
Make only changes you can justify, each with a short reason. Returning no edits is a valid answer for a
draft that is already sound."""


def _tool() -> dict:
    return {"toolSpec": {"name": REVIEW_TOOL, "description": "Edits to the draft ontology, each with a reason.",
            "inputSchema": {"json": {"type": "object", "required": ["edits"], "properties": {
                "edits": {"type": "array", "items": {"type": "object", "required": ["op", "kind", "term", "reason"],
                          "properties": {
                              "op": {"type": "string", "enum": list(OPS)},
                              "kind": {"type": "string", "enum": list(KINDS)},
                              "term": {"type": "string", "description": "the term's name as given in the draft"},
                              "value": {"type": ["string", "null"], "description":
                                        "set_parent: the parent class or null; merge: the term to keep; set_domain and "
                                        "set_range: a class; set_datatype: a datatype; drop: null"},
                              "reason": {"type": "string"}}}},
            }}}}}


def draft_view(defn: dict, aggregated: dict | None) -> str:
    """The draft as the reviewer sees it: compact JSON with document support per term."""
    support: dict[str, int] = {}
    for kind in KINDS:
        for row in (aggregated or {}).get(kind) or []:
            for name in [row["name"], *row.get("also", [])]:
                support[model.normalise(name)] = max(support.get(model.normalise(name), 0), row.get("docs", 0))

    def docs(t: dict) -> int | None:
        names = [t.get("name", ""), *(t.get("merged_from") or [])]
        found = [support[model.normalise(n)] for n in names if model.normalise(n) in support]
        return max(found) if found else None

    view = {
        "classes": [{"name": c["name"], "parent": c.get("parent"), "definition": c.get("definition"),
                     "docs": docs(c)} for c in defn.get("classes") or []],
        "relations": [{"name": r["name"], "domain": r.get("domain"), "range": r.get("range"),
                       "definition": r.get("definition"), "docs": docs(r)} for r in defn.get("relations") or []],
        "attributes": [{"name": a["name"], "domain": a.get("domain"), "datatype": a.get("datatype"),
                        "definition": a.get("definition"), "docs": docs(a)} for a in defn.get("attributes") or []],
    }
    return json.dumps(view, indent=1)


def review(client, model_id: str, defn: dict, aggregated: dict | None, profile: Profile) -> tuple[list[dict], dict]:
    """The reviewer's edits and the call's usage."""
    from .discover import _call
    res, usage = _call(client, model_id, REVIEW_SYSTEM.format(profile=profile.prompt_context()),
                       draft_view(defn, aggregated), _tool(), 8000)
    return [e for e in res.get("edits") or [] if isinstance(e, dict)], usage


class _Draft:
    """The consolidated definition, indexed by normalised name, with the edit operations."""

    def __init__(self, defn: dict):
        self.d = copy.deepcopy(defn)
        for kind in KINDS:
            self.d.setdefault(kind, [])

    def find(self, kind: str, name) -> dict | None:
        key = model.normalise(str(name or ""))
        return next((t for t in self.d[kind] if model.normalise(t["name"]) == key), None)

    def is_class(self, name) -> bool:
        return self.find("classes", name) is not None

    def ancestors(self, name: str) -> set[str]:
        seen: set[str] = set()
        cur = self.find("classes", name)
        while cur and cur.get("parent") and model.normalise(cur["parent"]) not in seen:
            seen.add(model.normalise(cur["parent"]))
            cur = self.find("classes", cur["parent"])
        return seen

    def repoint(self, old: str, new: str | None) -> list[str]:
        """Refer to class `new` wherever class `old` was referred to; with new None, drop what
        depends on old (relations and attributes) and lift old's children to old's parent."""
        effects = []
        gone = self.find("classes", old)
        for c in self.d["classes"]:
            if c.get("parent") and model.normalise(c["parent"]) == model.normalise(old):
                c["parent"] = new if new is not None else (gone or {}).get("parent")
        for kind, fields in (("relations", ("domain", "range")), ("attributes", ("domain",))):
            keep = []
            for t in self.d[kind]:
                hit = [f for f in fields if t.get(f) and model.normalise(t[f]) == model.normalise(old)]
                if hit and new is None:
                    effects.append(f"dropped {kind[:-1]} {t['name']} (its {hit[0]} was {old})")
                    continue
                for f in hit:
                    t[f] = new
                keep.append(t)
            self.d[kind] = keep
        return effects

    def apply(self, e: dict) -> str | None:
        """Apply one edit; None if applied, else why it was skipped."""
        op, kind, value = e.get("op"), e.get("kind"), e.get("value")
        if op not in OPS or kind not in KINDS:
            return "unknown op or kind"
        t = self.find(kind, e.get("term"))
        if t is None:
            return f"no {kind[:-1]} named {e.get('term')!r}"
        if op == "set_parent":
            if kind != "classes":
                return "set_parent applies to classes"
            if value is None or str(value).strip().lower() in ("", "null", "none"):
                t["parent"] = None
                return None
            p = self.find("classes", value)
            if p is None:
                return f"no class named {value!r}"
            if p is t or model.normalise(t["name"]) in self.ancestors(p["name"]) | {model.normalise(p["name"])}:
                return f"{value} under {t['name']} would make a cycle"
            t["parent"] = p["name"]
            return None
        if op == "merge":
            into = self.find(kind, value)
            if into is None or into is t:
                return f"no other {kind[:-1]} named {value!r} to merge into"
            names = [t["name"], t.get("label"), *(t.get("synonyms") or [])]
            into["synonyms"] = sorted({*(into.get("synonyms") or []), *(n for n in names if n)} - {into["name"]})
            into["merged_from"] = sorted({*(into.get("merged_from") or []), t["name"]})
            self.d[kind].remove(t)
            if kind == "classes":
                self.repoint(t["name"], into["name"])
            return None
        if op == "drop":
            self.d[kind].remove(t)
            if kind == "classes":
                e["effects"] = self.repoint(t["name"], None)
            return None
        if op in ("set_domain", "set_range"):
            if kind == "classes" or (op == "set_range" and kind != "relations"):
                return f"{op} does not apply to {kind}"
            if not self.is_class(value):
                return f"no class named {value!r}"
            t["domain" if op == "set_domain" else "range"] = self.find("classes", value)["name"]
            return None
        if kind != "attributes":
            return "set_datatype applies to attributes"
        if value not in model.DATATYPES:
            return f"{value!r} is not one of {sorted(model.DATATYPES)}"
        t["datatype"] = value
        return None


def apply_edits(defn: dict, edits: list[dict]) -> tuple[dict, list[dict], list[dict]]:
    """The edited definition, the edits applied (with their effects) and those skipped (with why).
    Edits apply in order, so a later edit sees the result of an earlier one."""
    draft = _Draft(defn)
    applied, skipped = [], []
    for e in edits:
        e = dict(e)
        why = draft.apply(e)
        if why:
            skipped.append({**e, "skipped": why})
        else:
            applied.append(e)
    return draft.d, applied, skipped
