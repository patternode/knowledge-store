"""Refine: bronze -> silver. Parse, then chunk into passages.

A document is refined once; the silver document's presence is the marker. A parser
or chunker upgrade is applied by --reparse, deliberately, because new passage ids mean
the document's gold facts cite passages that no longer exist and it must be re-extracted.
"""

from __future__ import annotations

import json
import logging

from .. import layout
from ..refine import UnsupportedFormat, parse
from ..refine.chunk import CHUNKER_VERSION, Passage, chunk_text
from ..store import Store, put_json
from .ingest import bronze_objects

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
    if len(res.text.strip()) < MIN_TEXT_CHARS:
        return {"doc_id": doc_id, "status": "empty", "reason": f"under {MIN_TEXT_CHARS} characters of text"}
    passages = chunk_text(res.text, doc_id)
    lake.put(layout.passages_key(doc_id),
             "\n".join(json.dumps(p.to_dict()) for p in passages).encode(), "application/x-ndjson")
    doc = {
        "doc_id": doc_id, "title": res.title or meta.get("name"), "source": meta["source"],
        "scope": meta.get("scope", "public"), "source_uri": meta.get("source_uri"),
        "name": meta.get("name"), "metadata": {**meta.get("metadata", {}), **res.metadata},
        "parser": res.parser, "chunker": CHUNKER_VERSION, "chars": len(res.text),
        "passages": len(passages), "text": res.text,
    }
    put_json(lake, layout.doc_key(doc_id), doc)  # written last: its presence marks the document refined
    return {"doc_id": doc_id, "status": "refined", "passages": len(passages)}


def refine_all(lake: Store, *, reparse: bool = False, limit: int | None = None) -> list[dict]:
    rows = []
    for doc_id, meta in bronze_objects(lake).items():
        if limit is not None and len(rows) >= limit:
            break
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
