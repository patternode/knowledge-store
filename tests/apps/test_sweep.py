"""The pipeline sweep (apps/sweep.py) end to end over a local lake with a fake model: one sweep at
a time, every collection in turn, and a failing collection recorded without stopping the rest."""

from __future__ import annotations

import json
import time

import pytest

from fake_llm import FakeClient
from knowledge_store.apps import sweep
from knowledge_store.platform_services.adapters.store import LocalStore
from knowledge_store.platform_services.domain import layout
from knowledge_store.platform_services.ports import put_json
from knowledge_store.platform_services.slices import collections
from test_lifecycle import DOCS, PROFILE


def collection(root, cid, mode="auto", docs=DOCS):
    for n, b in docs.items():
        root.put(f"landing/{cid}/{n}", b.encode())
    lk = collections.scoped(root, cid)
    put_json(lk, layout.CONFIG_SOURCES, [{"name": "docs", "type": "s3_landing", "options": {"prefix": f"landing/{cid}/"}}])
    put_json(lk, layout.CONFIG_SETTINGS, {"ontology_mode": mode, "discovery_min_docs": 3, "discovery_resamples": 1})
    put_json(lk, layout.CONFIG_PROFILE, PROFILE.to_dict())
    return lk


def status(lk):
    return json.loads(lk.get(layout.STATUS))


@pytest.fixture
def root(tmp_path):
    return LocalStore(tmp_path / "lake")


def test_an_upload_goes_all_the_way_to_ready_in_auto_mode(root):
    put_json(root, collections.CONFIG, [{"id": "m"}])
    lk = collection(root, "m")
    out = sweep.run(root, FakeClient, "fake")
    assert list(out) == ["m"] and out["m"][0]["ingest"]["docs"]["stored"] == len(DOCS)
    s = status(lk)
    assert s["stage"] == "ready" and s["active_version"] == "0.1.0" and s["silver_documents"] == len(DOCS)
    assert not root.exists(layout.PIPELINE_LOCK)


def test_a_second_sweep_does_only_the_missing_work(root):
    put_json(root, collections.CONFIG, [{"id": "m"}])
    collection(root, "m")
    sweep.run(root, FakeClient, "fake")
    again = sweep.run(root, FakeClient, "fake")["m"]
    assert len(again) == 1 and again[0]["refined"] == 0 and again[0]["extracted"] == 0


def test_in_curated_mode_extraction_waits_for_a_published_ontology(root):
    put_json(root, collections.CONFIG, [{"id": "m"}])
    lk = collection(root, "m", mode="curated")
    sweep.run(root, FakeClient, "fake")
    s = status(lk)
    assert s["stage"] == "awaiting_curation" and s["active_version"] is None and len(s["drafts"]) == 1


def test_too_few_documents_wait(root):
    put_json(root, collections.CONFIG, [{"id": "m"}])
    lk = collection(root, "m", docs=dict(list(DOCS.items())[:1]))
    sweep.run(root, FakeClient, "fake")
    s = status(lk)
    assert s["stage"] == "waiting_for_documents" and s["needed"] == 3


def test_only_sweeps_the_named_collections(root):
    put_json(root, collections.CONFIG, [{"id": "a"}, {"id": "b"}])
    collection(root, "a", mode="curated")
    collection(root, "b", mode="curated")
    assert list(sweep.run(root, FakeClient, "fake", only=["b"])) == ["b"]


def test_a_failing_collection_is_recorded_and_the_others_go_on(root, monkeypatch):
    put_json(root, collections.CONFIG, [{"id": "a"}, {"id": "b"}])
    bad, good = collection(root, "a", mode="curated"), collection(root, "b", mode="curated")
    real = sweep.sweep_once

    def flaky(lake, *a):
        if lake.prefix.endswith("/a/"):
            raise RuntimeError("disk full")
        return real(lake, *a)
    monkeypatch.setattr(sweep, "sweep_once", flaky)
    out = sweep.run(root, FakeClient, "fake")
    assert "disk full" in out["a"][0]["failed"] and status(bad)["stage"] == "failed"
    assert status(good)["stage"] == "awaiting_curation"


def test_a_held_lock_means_nothing_to_do(root):
    put_json(root, collections.CONFIG, [{"id": "m"}])
    collection(root, "m")
    assert sweep.acquire(root, "other")
    assert sweep.run(root, FakeClient, "fake") == {}
    assert json.loads(root.get(layout.PIPELINE_LOCK))["owner"] == "other"


def test_a_stale_lock_is_taken_over(root):
    root.put(layout.PIPELINE_LOCK, json.dumps({"owner": "dead", "at": time.time() - sweep.LOCK_TTL_S - 1}).encode())
    assert sweep.acquire(root, "me") and json.loads(root.get(layout.PIPELINE_LOCK))["owner"] == "me"


def test_an_unreadable_lock_is_respected(root):
    root.put(layout.PIPELINE_LOCK, b"not json")
    assert not sweep.acquire(root, "me")


def test_settings_default_and_take_the_lakes_values(root):
    assert sweep.settings(root) == sweep.DEFAULT_SETTINGS
    put_json(root, layout.CONFIG_SETTINGS, {"ontology_mode": "auto"})
    assert sweep.settings(root)["ontology_mode"] == "auto" and sweep.settings(root)["extraction_workers"] == 4
