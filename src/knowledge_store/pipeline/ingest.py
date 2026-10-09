"""Ingest: every configured source -> bronze.

For each item an adapter lists: if its (key, version) was stored before, skip it without
reading it. Otherwise fetch the bytes, content-address them (sha256), and write the bronze
object and its meta.json unless that content is already there. The same file uploaded under
two names is one bronze object with two _seen records.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from dataclasses import dataclass

from .. import adapters, layout
from ..config import SourceConfig
from ..store import Store, put_json

log = logging.getLogger("ingest")


@dataclass
class IngestStats:
    listed: int = 0
    skipped: int = 0
    stored: int = 0
    duplicate: int = 0
    failed: int = 0

    def as_dict(self) -> dict:
        return dict(self.__dict__)


def ingest_source(lake: Store, source: SourceConfig, *, limit: int | None = None) -> tuple[IngestStats, list[dict]]:
    # Adapters read from the whole lake (landing/ is outside any collection's prefix).
    adapter = adapters.build(source, getattr(lake, "whole", lake))
    stats, rows = IngestStats(), []
    for item in adapter.items():
        if limit is not None and stats.stored + stats.duplicate >= limit:
            break
        stats.listed += 1
        seen = layout.seen_key(source.name, item.key)
        if item.version and lake.exists(seen):
            prior = json.loads(lake.get(seen))
            if prior.get("version") == item.version:
                stats.skipped += 1
                continue
        try:
            data = adapter.fetch(item)
        except Exception as e:  # one bad item never stops a source
            stats.failed += 1
            rows.append({"source": source.name, "key": item.key, "status": "fetch_failed", "error": repr(e)[:500]})
            log.warning("%s: fetch %s failed: %r", source.name, item.key, e)
            continue
        digest = layout.sha256(data)
        meta_key = layout.bronze_meta_key(source.name, digest)
        if lake.exists(meta_key):
            stats.duplicate += 1
            status = "duplicate"
            # The same bytes under a second name stay one object. Bind has to see every name:
            # the first upload is often not the path the mapping names.
            meta = json.loads(lake.get(meta_key))
            keys = list(dict.fromkeys([*(meta.get("source_keys") or [meta.get("source_key")]), item.key]))
            if keys != meta.get("source_keys"):
                meta["source_keys"] = keys
                put_json(lake, meta_key, meta)
        else:
            ext = item.extension()
            lake.put(layout.bronze_content_key(source.name, digest, ext), data,
                     item.content_type or "application/octet-stream")
            put_json(lake, meta_key, {
                "doc_id": digest, "source": source.name, "adapter": source.type, "scope": source.scope,
                "source_key": item.key, "source_uri": item.uri, "source_version": item.version,
                "source_keys": [item.key],
                "name": item.name, "ext": ext, "content_type": item.content_type, "bytes": len(data),
                "metadata": item.metadata, "fetched_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
            })
            stats.stored += 1
            status = "stored"
        put_json(lake, seen, {"key": item.key, "version": item.version, "doc_id": digest})
        rows.append({"source": source.name, "key": item.key, "doc_id": digest, "status": status})
    return stats, rows


def bronze_objects(lake: Store) -> dict[str, dict]:
    """doc_id -> meta for every bronze object (the first source wins for a duplicate)."""
    out: dict[str, dict] = {}
    for key in lake.list(layout.BRONZE + "/"):
        if key.startswith(layout.SEEN + "/") or not key.endswith("/meta.json"):
            continue
        meta = json.loads(lake.get(key))
        meta["content_key"] = key.rsplit("/", 1)[0] + "/content" + meta["ext"]
        out.setdefault(meta["doc_id"], meta)
    return out
