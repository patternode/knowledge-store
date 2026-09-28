"""The extraction tool schema, generated from the ontology.

The model answers with four lists:

    entities    typed things it found, each with a ref ("e1") the other lists point at
    attributes  literal values of an entity's attribute properties
    relations   subject -> predicate -> object between entity refs
    candidates  things the ontology has no term for: the growth signal for the next version

Candidates are what keep a frozen ontology honest. Without an escape hatch a model forces a
fact into the nearest term or drops it silently; with one, the gap is recorded with its
evidence and nothing out of vocabulary enters the graph. (In practice, mining a catch-all like this is how an ontology's next version is found.)
"""

from __future__ import annotations

from ..ontology.model import OntologySpec

TOOL_NAME = "record_knowledge"
PROMPT_VERSION = "kl-extract-v1"
CANDIDATE_KINDS = ("class", "relation", "attribute")


def _cites() -> dict:
    return {"type": "array", "minItems": 1, "items": {"type": "string"},
            "description": "ids of the passages this is stated in"}


def tool_spec(spec: OntologySpec, *, only: set[str] | None = None, known_refs: list[str] | None = None) -> dict:
    """only: a delta run's focus terms. Entity types are then the focus classes plus the
    classes the focus properties reference; known_refs are refs of entities already held
    for the document, which the model may use as endpoints without declaring them again."""
    classes = sorted(spec.classes)
    rels = sorted(p for p in spec.relations if only is None or p in only)
    attrs = sorted(p for p in spec.attributes if only is None or p in only)
    if only is not None:
        needed = set(c for c in only if c in spec.classes)
        for p in rels:
            needed |= set(spec.relations[p].domain) | set(spec.relations[p].range)
        for p in attrs:
            needed |= set(spec.attributes[p].domain)
        classes = sorted(needed & set(spec.classes)) or classes
    ref_note = "a ref declared in entities"
    if known_refs:
        ref_note += f", or a known entity's ref ({known_refs[0]}...)"
    props: dict = {
        "entities": {"type": "array", "items": {"type": "object",
            "required": ["ref", "type", "name", "passage_ids"],
            "properties": {
                "ref": {"type": "string", "description": "a short id unique in this call, e.g. e1"},
                "type": {"type": "string", "enum": classes},
                "name": {"type": "string", "description": "the name as written in the passage"},
                "aliases": {"type": "array", "items": {"type": "string"},
                            "description": "other names the document uses for the same thing"},
                "passage_ids": _cites(),
            }}},
    }
    if attrs:
        props["attributes"] = {"type": "array", "items": {"type": "object",
            "required": ["entity", "property", "value", "passage_ids"],
            "properties": {
                "entity": {"type": "string", "description": ref_note},
                "property": {"type": "string", "enum": attrs},
                "value": {"type": "string", "description": "the value exactly as written; a number as its digits"},
                "passage_ids": _cites(),
            }}}
    if rels:
        props["relations"] = {"type": "array", "items": {"type": "object",
            "required": ["subject", "predicate", "object", "passage_ids"],
            "properties": {
                "subject": {"type": "string", "description": ref_note},
                "predicate": {"type": "string", "enum": rels},
                "object": {"type": "string", "description": ref_note},
                "passage_ids": _cites(),
            }}}
    props["candidates"] = {"type": "array", "items": {"type": "object",
        "required": ["kind", "term", "definition", "evidence", "passage_ids"],
        "properties": {
            "kind": {"type": "string", "enum": list(CANDIDATE_KINDS)},
            "term": {"type": "string", "description": "a short name for the missing type, relation or attribute"},
            "definition": {"type": "string", "description": "one sentence: what it means, in general terms"},
            "evidence": {"type": "string", "description": "a short span copied verbatim from the passage"},
            "nearest": {"type": ["string", "null"], "description": "the closest existing term, if any"},
            "passage_ids": _cites(),
        }}}
    return {"toolSpec": {
        "name": TOOL_NAME,
        "description": "Record the entities, attributes and relations stated in the passages, typed by the "
                       "ontology, each citing its passages; and any concept the ontology has no term for.",
        "inputSchema": {"json": {"type": "object", "required": ["entities", "candidates"], "properties": props}},
    }}
