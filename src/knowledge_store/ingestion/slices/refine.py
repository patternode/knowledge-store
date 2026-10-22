"""Refine: bronze -> silver. Parse, conform, then chunk into passages.

A document is refined once; the silver document's presence is the marker. A parser,
conformer or chunker upgrade is applied by --reparse, deliberately, because new passage
ids mean the document's gold facts cite passages that no longer exist and it must be
re-extracted.

Conformance is generic. It rewrites dates, times and numbers into one form and does not
consult an ontology. The bronze bytes stay as uploaded.
"""

from __future__ import annotations

from collections.abc import Collection

import json
import logging

from knowledge_store.platform_services import layout
from knowledge_store.ingestion.domain.conform import CONFORMER_VERSION, conform
from knowledge_store.ingestion.domain.parsing import UnsupportedFormat, parse
from knowledge_store.ingestion.domain.chunk import CHUNKER_VERSION, Passage, chunk_text
from knowledge_store.platform_services import Store, put_json
from knowledge_store.ingestion.slices.ingest import bronze_objects

log = logging.getLogger("refine")

MIN_TEXT_CHARS = 40


def refine_one(lake: Store, meta: dict) -> dict:
    doc_id = meta["doc_id"]
    data = lake.get(meta["content_key"])
    try:
        res = parse(data, meta["ext"], meta.get("content_type"))
    except UnsupportedFormat as e:
        return {"doc_id": doc_id, "status": "unsupported", "reason": str(e)}
    except Exception as e:  # a malformed file is recorded, not fatal
        return {"doc_id": doc_id, "status": "parse_failed", "reason": repr(e)[:500]}
    conformed = conform(res.text)
    if len(conformed.text.strip()) < MIN_TEXT_CHARS:
        return {"doc_id": doc_id, "status": "empty", "reason": f"under {MIN_TEXT_CHARS} characters of text"}
    passages = chunk_text(conformed.text, doc_id)
    lake.put(layout.passages_key(doc_id),
             "\n".join(json.dumps(p.to_dict()) for p in passages).encode(), "application/x-ndjson")
    meta_out = {**meta.get("metadata", {}), **res.metadata}
    if conformed.rules:
        meta_out["conform"] = [dict(rule) for rule in conformed.rules]
    title = conform(res.title).text if res.title else None
    doc = {
        "doc_id": doc_id, "title": title or meta.get("name"), "source": meta["source"],
        "scope": meta.get("scope", "public"), "source_uri": meta.get("source_uri"),
        "name": meta.get("name"), "metadata": meta_out,
        "parser": res.parser, "conformer": CONFORMER_VERSION, "chunker": CHUNKER_VERSION,
        "chars": len(conformed.text), "passages": len(passages), "text": conformed.text,
    }
    put_json(lake, layout.doc_key(doc_id), doc)  # written last: its presence marks the document refined
    return {"doc_id": doc_id, "status": "refined", "passages": len(passages)}


def refine_all(lake: Store, *, reparse: bool = False, limit: int | None = None,
               mapped: Collection[str] = ()) -> list[dict]:
    """Parse every bronze object not yet refined. mapped names the documents a table mapping
    claims (Extraction's mapped_doc_ids): they are tables, not documents, and are skipped. The
    caller supplies them, so Ingestion does not depend on Extraction."""
    mapped = set(mapped)
    rows = []
    for doc_id, meta in bronze_objects(lake).items():
        if limit is not None and len(rows) >= limit:
            break
        if doc_id in mapped:
            if not lake.exists(layout.skipped_key(doc_id)):
                row = {"doc_id": doc_id, "status": "mapped", "reason": "a mapping names this file, so it is a table, not a document"}
                put_json(lake, layout.skipped_key(doc_id), row)
                rows.append(row)
            continue
        if not reparse and (lake.exists(layout.doc_key(doc_id)) or lake.exists(layout.skipped_key(doc_id))):
            continue
        row = refine_one(lake, meta)
        rows.append(row)
        if row["status"] != "refined":
            put_json(lake, layout.skipped_key(doc_id), row)
            log.info("%s: %s (%s)", doc_id[:12], row["status"], row.get("reason"))
    return rows


def silver_doc_ids(lake: Store) -> list[str]:
    return [layout.doc_id_from_key(k) for k in lake.list(layout.SILVER_DOCS + "/") if k.endswith(".json")]


def load_doc(lake: Store, doc_id: str) -> dict:
    return json.loads(lake.get(layout.doc_key(doc_id)))


def load_passages(lake: Store, doc_id: str) -> list[Passage]:
    body = lake.get(layout.passages_key(doc_id)).decode()
    return [Passage.from_dict(json.loads(line)) for line in body.splitlines() if line.strip()]
