"""The ontology-guided extraction loop, per document.

1. The model reads the numbered passages, the collection profile and the ontology vocabulary,
   and must answer by calling record_knowledge, whose schema is generated from the ontology.
2. The result is checked: shape and ontology (types, domains, ranges), grounding (cited
   passages exist, names and values are in them), then RDF and SHACL.
3. Errors go back to the model as the tool result and it corrects its call, at most
   MAX_REPAIRS rounds. Whatever still fails is dropped item by item (dropping an entity drops
   what hangs off it), so one bad fact never costs a document its good ones.
"""

from __future__ import annotations

import copy
import logging
import random
import re
import time
from dataclasses import dataclass, field

from rdflib import Graph

from ..config import Profile
from ..ontology.model import CORE_SHAPES, CORE_TTL, OntologySpec
from ..refine.chunk import Passage
from .rdf import build_graph, label_messages
from .schema import PROMPT_VERSION, TOOL_NAME, tool_spec
from .validate import clean_candidates, grounding_errors, shacl_errors, shape_errors

log = logging.getLogger("extract")

MAX_REPAIRS = 2
THROTTLE_ATTEMPTS = 10
MAX_INPUT_CHARS = 400_000
USAGE_KEYS = ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheWriteInputTokens")

SYSTEM = """You extract knowledge from documents into an ontology.

{profile}

Rules:
- Record only what the passages state. Never infer, compute or recall a fact from outside them.
- Every entity, attribute and relation cites the ids of the passages it is stated in.
- An entity's name is copied as written in a passage. Give other names the document uses as aliases.
- One entity per real-world thing in this document: declare it once and refer to it by its ref.
- Use the most specific entity type that fits. Attribute values are copied as written; numbers as their digits.
- A relation's subject and object must have types its signature allows.
- When something important in the passages has no fitting type, relation or attribute in the ontology,
  do not force it into the nearest term. Record it under candidates, with a one-sentence definition,
  a short verbatim evidence span and the closest existing term. Candidates are how the ontology grows.
- An empty list is a valid answer.

Ontology vocabulary:
{vocabulary}
"""

DELTA_NOTE = """
This is a delta run: the ontology gained the terms above, and facts in the other terms are already
held. Extract only facts in the terms listed. The known entities below are already in the graph; refer
to them by their ref (k1, k2, ...) rather than declaring them again. You may declare a new entity when a
new term needs one.
"""


@dataclass
class ExtractionOutcome:
    result: dict
    graph: Graph
    candidates: list[dict]
    repairs: int
    dropped: list[str] = field(default_factory=list)
    usage: dict = field(default_factory=dict)


def render_passages(passages: list[Passage]) -> str:
    out, size = [], 0
    for p in passages:
        block = f"<passage id=\"{p.passage_id}\">\n{p.text}\n</passage>"
        if size + len(block) > MAX_INPUT_CHARS:
            out.append("<truncated/>")
            break
        out.append(block)
        size += len(block)
    return "\n".join(out)


class Extractor:
    def __init__(self, client, model_id: str, spec: OntologySpec, profile: Profile, *,
                 only: set[str] | None = None, max_tokens: int = 32000, shapes: Graph | None = None):
        """only: the focus terms of a delta run. shapes: the ontology version's own SHACL,
        applied with the core provenance shapes."""
        self.client = client
        self.model_id = model_id
        self.spec = spec
        self.profile = profile
        self.only = only
        self.max_tokens = max_tokens
        vocab = spec.vocabulary_prompt(only)
        self.system = SYSTEM.format(profile=profile.prompt_context(), vocabulary=vocab) + (DELTA_NOTE if only else "")
        self.shapes = Graph().parse(str(CORE_SHAPES), format="turtle")
        if shapes is not None:
            self.shapes += shapes
        self.tbox = Graph().parse(str(CORE_TTL), format="turtle")
        if spec.graph is not None:
            self.tbox += spec.graph

    def request_body(self, messages: list[dict], tool: dict, *, batch: bool = False) -> dict:
        system = [{"text": self.system}] + ([] if batch else [{"cachePoint": {"type": "default"}}])
        return dict(system=system, messages=messages,
                    toolConfig={"tools": [tool], "toolChoice": {"tool": {"name": TOOL_NAME}}},
                    inferenceConfig={"maxTokens": self.max_tokens, "temperature": 0})

    @staticmethod
    def first_messages(doc: dict, passages: list[Passage], known: dict[str, dict] | None = None) -> list[dict]:
        head = f"Document: {doc.get('title') or doc.get('name') or doc['doc_id']} (source: {doc.get('source')})."
        if known:
            rows = "\n".join(f"- {ref}: {v['type']} \"{v['name']}\"" for ref, v in known.items())
            head += f"\n\nKnown entities:\n{rows}"
        return [{"role": "user", "content": [{"text": f"{head}\n\n{render_passages(passages)}"}]}]

    def _converse(self, messages: list[dict], tool: dict) -> dict:
        kwargs = {"modelId": self.model_id, **self.request_body(messages, tool)}
        for attempt in range(THROTTLE_ATTEMPTS):
            try:
                return self.client.converse(**kwargs)
            except Exception as e:
                name = type(e).__name__
                if "Throttl" in name or "Throttl" in str(e) or "ServiceUnavailable" in name:
                    time.sleep(min(120, 2 ** attempt * 2) * (0.5 + random.random()))
                    continue
                raise
        raise RuntimeError(f"model throttled {THROTTLE_ATTEMPTS} times in a row")

    @staticmethod
    def _tool_use(resp: dict) -> dict:
        for block in resp["output"]["message"]["content"]:
            if "toolUse" in block:
                return block["toolUse"]
        raise RuntimeError(f"model did not call the extraction tool (stopReason {resp.get('stopReason')})")

    def _check(self, result: dict, doc: dict, passages: list[Passage], run: dict,
               known: dict[str, dict] | None) -> tuple[list[str], Graph | None]:
        known_types = {k: v["type"] for k, v in (known or {}).items()}
        errors = shape_errors(result, self.spec, known_types)
        if errors:
            return errors, None
        errors = grounding_errors(result, self.spec, passages)
        try:
            g, where = build_graph(result, spec=self.spec, doc=doc, passages=passages, run=run, known=known)
            conforms, msgs, _ = shacl_errors(g, self.shapes, self.tbox)
        except (KeyError, ValueError, TypeError, AttributeError, ArithmeticError) as e:
            return errors + [f"result could not be converted: {e!r}"], None
        if not conforms:
            errors += label_messages(msgs, where)
        return errors, g

    def extract(self, doc: dict, passages: list[Passage], run: dict, *,
                known: dict[str, dict] | None = None, first_response: dict | None = None) -> ExtractionOutcome:
        known_refs = list(known or {})
        tool = tool_spec(self.spec, only=self.only, known_refs=known_refs)
        messages = self.first_messages(doc, passages, known)
        usage = dict.fromkeys(USAGE_KEYS, 0)
        repairs = 0
        pending = first_response
        while True:
            resp, pending = (pending, None) if pending is not None else (self._converse(messages, tool), None)
            for k in usage:
                usage[k] += resp.get("usage", {}).get(k, 0)
            tu = self._tool_use(resp)
            result = tu["input"] if isinstance(tu["input"], dict) else {}
            errors, g = self._check(result, doc, passages, run, known)
            if not errors and g is not None:
                cands, _ = clean_candidates(result, passages)
                return ExtractionOutcome(result, g, cands, repairs, usage=usage)
            if repairs >= MAX_REPAIRS:
                return self._salvage(result, doc, passages, run, known, repairs, usage, errors)
            repairs += 1
            log.info("%s repair %d: %d errors", doc["doc_id"][:12], repairs, len(errors))
            messages += [
                resp["output"]["message"],
                {"role": "user", "content": [{"toolResult": {
                    "toolUseId": tu["toolUseId"], "status": "error",
                    "content": [{"text": "The call was rejected. Fix these problems and call "
                                 f"{TOOL_NAME} again with the complete corrected result:\n- "
                                 + "\n- ".join(errors[:40])}]}}]},
            ]

    def _salvage(self, result, doc, passages, run, known, repairs, usage, errors) -> ExtractionOutcome:
        kept = copy.deepcopy(result)
        dropped: list[str] = []
        for _ in range(5):
            bad: dict[str, set[int]] = {}
            for e in errors:
                m = re.match(r"(entities|attributes|relations)\[(\d+)\]", e)
                if m:
                    bad.setdefault(m[1], set()).add(int(m[2]))
            if not bad:
                break
            gone_refs = {kept["entities"][i]["ref"] for i in bad.get("entities", ())
                         if i < len(kept.get("entities") or []) and isinstance(kept["entities"][i], dict)}
            for sec, idx in bad.items():
                items = kept.get(sec) or []
                dropped += [f"{sec}[{i}]" for i in sorted(idx)]
                kept[sec] = [it for i, it in enumerate(items) if i not in idx]
            if gone_refs:
                kept["attributes"] = [a for a in kept.get("attributes") or [] if a.get("entity") not in gone_refs]
                kept["relations"] = [r for r in kept.get("relations") or []
                                     if r.get("subject") not in gone_refs and r.get("object") not in gone_refs]
            errors, g = self._check(kept, doc, passages, run, known)
            if not errors and g is not None:
                cands, _ = clean_candidates(result, passages)
                return ExtractionOutcome(kept, g, cands, repairs, dropped=dropped, usage=usage)
        raise ValueError(f"{doc['doc_id'][:12]}: still invalid after salvage: {errors[:5]}")


def run_record(run_id: str, model_id: str, version: str, *, delta: bool = False) -> dict:
    return {"run_id": run_id, "model_id": model_id, "prompt_version": PROMPT_VERSION,
            "ontology_version": version, "delta": delta}
