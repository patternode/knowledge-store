"""Open facts: schema-free triples from every silver passage, the floor under the typed graph.

The typed extraction (extract.py) records what the active ontology names and nothing else, so
a hop the ontology has no term for is absent from the graph. This slice records every fact a
passage states as a plain triple, subject, predicate, object, in the passage's own words, with
no schema (the HippoRAG 2 design, Gutiérrez et al. 2025). The walk (knowledge_graph/slices/walk.py)
spreads over these to find the passages connected to a question across documents; the typed graph
stays the layer a precise question is answered from.

One model call a batch of passages (PASSAGES_PER_CALL, so the answer stays well inside the output
limit): the model names the things each passage mentions, then records triples whose subject and
object are among them, copied as written, by calling record_facts. A fact names the passage it was
read from; one whose passage id is unknown is dropped, and one whose subject or object is not found
in that passage's text is kept but marked ungrounded, so the walk can weight it down.
silver/facts/<doc id>.json holds a document's facts; a document that has one is not sent again
unless redo says so. Nothing here reads the ontology.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from knowledge_store.ingestion import load_doc, load_passages, silver_doc_ids
from knowledge_store.extraction.slices.extractor import THROTTLE_ATTEMPTS, USAGE_KEYS, render_passages
from knowledge_store.platform_services import Store, layout, put_json

log = logging.getLogger("open_facts")

TOOL_NAME = "record_facts"
MAX_TEXT = 80
MAX_FACTS = 400
PASSAGES_PER_CALL = 4
MAX_OUTPUT_TOKENS = 6000

SYSTEM = """You extract the facts a document states, as triples between named things, for a search index.

For each passage, first find the named things it mentions: people, teams, organisations, products,
systems, services, documents, tickets, places, dates, amounts and codes. Then record the facts that
relate them, one triple each: a subject and an object that are both named things copied exactly as
the passage writes them (no pronouns, no rewording, at most a few words each), and a short predicate
in the passage's own words. Record the id of the passage the fact is read from. Record every relation
between named things, every attribute with its value, and every event with its date; skip opinions
and instructions. A passage usually holds several facts. Answer only by calling record_facts."""

TOOL = {"toolSpec": {"name": TOOL_NAME, "description": "Record the facts the passages state.",
                     "inputSchema": {"json": {"type": "object", "properties": {"facts": {"type": "array", "items": {
                         "type": "object",
                         "properties": {"subject": {"type": "string"}, "predicate": {"type": "string"},
                                        "object": {"type": "string"},
                                        "passage": {"type": "string", "description": "the id of the passage the fact is read from"}},
                         "required": ["subject", "predicate", "object", "passage"]}}},
                                     "required": ["facts"]}}}}


def facts_key(doc_id: str) -> str:
    return f"{layout.SILVER_FACTS}/{doc_id}.json"


def load_open_facts(lake: Store, doc_id: str) -> dict | None:
    key = facts_key(doc_id)
    return json.loads(lake.get(key)) if lake.exists(key) else None


def open_fact_rows(lake: Store) -> list[dict]:
    """Every document's facts as rows: s, p, o, pid (the passage), doc, grounded."""
    rows = []
    for key in lake.list(layout.SILVER_FACTS + "/"):
        if key.endswith(".json"):
            held = json.loads(lake.get(key))
            rows.extend({**f, "doc": held["doc_id"]} for f in held.get("facts", []))
    return rows


def clean_facts(raw, passages) -> tuple[list[dict], int]:
    """The usable facts of a model answer, and how many were dropped: a fact needs three non-empty
    strings and a known passage id; duplicates go; subject and object are looked for in the passage."""
    texts = {p.passage_id: p.text.lower() for p in passages}
    out, seen, dropped = [], set(), 0
    for f in (raw if isinstance(raw, list) else [])[:MAX_FACTS]:
        if not isinstance(f, dict):
            dropped += 1
            continue
        s, p, o = (str(f.get(k) or "").strip()[:MAX_TEXT] for k in ("subject", "predicate", "object"))
        pid = str(f.get("passage") or "").strip()
        if not (s and p and o) or pid not in texts:
            dropped += 1
            continue
        key = (s.lower(), p.lower(), o.lower(), pid)
        if key in seen:
            continue
        seen.add(key)
        text = texts[pid]
        out.append({"s": s, "p": p, "o": o, "pid": pid, "grounded": s.lower() in text and o.lower() in text})
    return out, dropped


def _converse(client, model_id: str, messages: list[dict]) -> dict:
    kwargs = dict(modelId=model_id, system=[{"text": SYSTEM}], messages=messages,
                  toolConfig={"tools": [TOOL], "toolChoice": {"tool": {"name": TOOL_NAME}}},
                  inferenceConfig={"maxTokens": MAX_OUTPUT_TOKENS, "temperature": 0})
    for attempt in range(THROTTLE_ATTEMPTS):
        try:
            return client.converse(**kwargs)
        except Exception as e:
            name = type(e).__name__
            if "Throttl" in name or "Throttl" in str(e) or "ServiceUnavailable" in name:
                time.sleep(min(120, 2 ** attempt * 2) * (0.5 + random.random()))
                continue
            raise
    raise RuntimeError(f"model throttled {THROTTLE_ATTEMPTS} times in a row")


def _tool_input(resp: dict) -> dict:
    for block in resp["output"]["message"]["content"]:
        if "toolUse" in block:
            return block["toolUse"].get("input") or {}
    raise RuntimeError(f"model did not call {TOOL_NAME} (stopReason {resp.get('stopReason')})")


def extract_doc(lake: Store, client, model_id: str, doc_id: str) -> dict:
    doc, passages = load_doc(lake, doc_id), load_passages(lake, doc_id)
    head = f"Document: {doc.get('title') or doc.get('name') or doc_id}."
    usage, facts, dropped = dict.fromkeys(USAGE_KEYS, 0), [], 0
    for start in range(0, len(passages), PASSAGES_PER_CALL):
        batch = passages[start:start + PASSAGES_PER_CALL]
        messages = [{"role": "user", "content": [{"text": f"{head}\n\n{render_passages(batch)}"}]}]
        resp = _converse(client, model_id, messages)
        for k in USAGE_KEYS:
            usage[k] += resp.get("usage", {}).get(k, 0)
        found, lost = clean_facts(_tool_input(resp).get("facts"), batch)
        facts += found
        dropped += lost
    held = {"doc_id": doc_id, "model": model_id, "passages": len(passages), "facts": facts, "dropped": dropped,
            "usage": usage, "extracted_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds")}
    put_json(lake, facts_key(doc_id), held)
    return {"doc_id": doc_id, "status": "extracted", "facts": len(facts),
            "grounded": sum(f["grounded"] for f in facts), "dropped": dropped, "usage": usage}


def extract_open_facts(lake: Store, client, model_id: str, *, workers: int = 4, limit: int | None = None,
                       redo: bool = False) -> dict:
    """Open facts for every silver document that has none yet (all of them with redo), limit at most."""
    todo = [d for d in silver_doc_ids(lake) if redo or not lake.exists(facts_key(d))]
    if limit is not None:
        todo = todo[:limit]
    rows: list[dict] = []
    with ThreadPoolExecutor(max(1, workers)) as ex:
        futures = {ex.submit(extract_doc, lake, client, model_id, d): d for d in todo}
        for fut in as_completed(futures):
            try:
                rows.append(fut.result())
            except Exception as e:  # one document's failure never stops the rest; it is redone next run
                log.exception("open facts failed for %s", futures[fut])
                rows.append({"doc_id": futures[fut], "status": "failed", "error": str(e)[:300]})
    usage = {k: sum(r.get("usage", {}).get(k, 0) for r in rows) for k in USAGE_KEYS}
    return {"documents": len(todo), "extracted": sum(r["status"] == "extracted" for r in rows),
            "failed": sum(r["status"] == "failed" for r in rows),
            "facts": sum(r.get("facts", 0) for r in rows), "grounded": sum(r.get("grounded", 0) for r in rows),
            "usage": usage, "rows": sorted(rows, key=lambda r: r["doc_id"])}
