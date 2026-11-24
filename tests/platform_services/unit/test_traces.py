"""Answer traces are written to the lake, private ones apart."""

import json

from knowledge_store.platform_services.adapters import traces
from knowledge_store.platform_services.adapters.store import LocalStore


def test_traces_are_written_by_day_and_private_ones_apart(tmp_path):
    store = LocalStore(str(tmp_path))
    traces.record({"at": "2026-11-24T10:00:00+00:00", "scopes": ["public"], "answer_id": "a"})
    traces.record({"at": "2026-11-24T10:01:00+00:00", "scopes": ["private"], "answer_id": "b"})
    traces.flush(store)
    keys = sorted(store.list("usage/traces/"))
    assert any(k.startswith("usage/traces/dt=2026-11-24/") for k in keys)
    assert any(k.startswith("usage/traces/scope=private/dt=2026-11-24/") for k in keys)
    rows = [json.loads(line) for k in keys for line in store.get(k).decode().splitlines()]
    assert sorted(r["answer_id"] for r in rows) == ["a", "b"]


def test_a_failed_write_never_raises(caplog):
    class Broken:
        def put(self, *a, **k):
            raise OSError("disk full")
    traces.record({"at": "2026-11-24T10:00:00+00:00", "answer_id": "c"})
    traces.flush(Broken())
    assert "trace write failed" in caplog.text
