"""Answer traces, written to the lake as JSON lines the way the ledger writes model calls.

usage/traces/dt=<date>/<part>-<seq>.jsonl, buffered and written every FLUSH_EVERY records and when
the process exits. A trace of a question asked with private scope goes under
usage/traces/scope=private/, so a grant on the public prefix never reaches it. A write that fails
logs the records instead and never fails the answer. The lake's lifecycle rule deletes traces after
the deployment's retention period (90 days by default), since a trace holds the question asked.
"""

from __future__ import annotations

import atexit
import json
import logging
import os
import threading
import uuid

log = logging.getLogger("traces")
PREFIX = "usage/traces"
FLUSH_EVERY = int(os.environ.get("TRACES_FLUSH_EVERY", "20"))


def _root() -> str:
    """The lake (LAKE_URI, or the bucket a Lambda is given as LAKE_BUCKET), or a local directory."""
    if os.environ.get("LAKE_URI"):
        return os.environ["LAKE_URI"]
    if os.environ.get("LAKE_BUCKET"):
        return f"s3://{os.environ['LAKE_BUCKET']}"
    return os.environ.get("LEDGER_ROOT", "build")


def key_for(trace: dict, part: str, seq: int) -> str:
    scope = "scope=private/" if "private" in (trace.get("scopes") or []) else ""
    return f"{PREFIX}/{scope}dt={str(trace.get('at', ''))[:10]}/{part}-{seq:04d}.jsonl"


class _Buffer:
    def __init__(self):
        self.lock = threading.Lock()
        self.rows: list[dict] = []
        self.part = uuid.uuid4().hex[:8]
        self.seq = 0

    def add(self, row: dict) -> None:
        with self.lock:
            self.rows.append(row)
            full = len(self.rows) >= FLUSH_EVERY
        if full:
            self.flush()

    def flush(self, store=None) -> None:
        with self.lock:
            rows, self.rows = self.rows, []
        groups: dict[str, list[dict]] = {}
        for r in rows:
            with self.lock:
                self.seq += 1
                seq = self.seq
            groups.setdefault(key_for(r, self.part, seq).rsplit("/", 1)[0], []).append(r)
        for prefix, group in groups.items():
            with self.lock:
                self.seq += 1
                seq = self.seq
            body = "\n".join(json.dumps(r, default=str) for r in group) + "\n"
            try:
                if store is None:
                    from knowledge_store.platform_services.adapters.store import store_from_uri
                    store = store_from_uri(_root())
                store.put(f"{prefix}/{self.part}-{seq:04d}.jsonl", body.encode(), "application/x-ndjson")
            except Exception as e:  # noqa: BLE001, a trace never breaks an answer
                log.warning("trace write failed (%s: %s); records follow", type(e).__name__, str(e)[:200])
                for r in group:
                    log.warning("trace %s", json.dumps(r, default=str))


_buffer = _Buffer()
atexit.register(_buffer.flush)


def record(trace: dict) -> None:
    _buffer.add(trace)


def flush(store=None) -> None:
    """Write buffered traces now (a Lambda or a test should call this)."""
    _buffer.flush(store)
