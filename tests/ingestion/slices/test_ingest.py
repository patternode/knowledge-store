"""Ingestion slice: ingest a source into bronze, through a fake source adapter and a local lake."""

from __future__ import annotations

import json

import pytest

from knowledge_store.ingestion.ports import SourceItem
from knowledge_store.ingestion.slices.ingest import IngestStats, bronze_objects, ingest
from knowledge_store.platform_services import SourceConfig, layout
from knowledge_store.platform_services.adapters.store import LocalStore

SOURCE = SourceConfig("docs", "fake", {}, scope="private")


class FakeSource:
    """A SourceAdapter over a dict: key -> (version, bytes). A bytes value of None fails the fetch."""

    type = "fake"

    def __init__(self, items: dict[str, tuple[str, bytes | None]], content_type: str | None = "text/plain"):
        self.data, self.content_type = items, content_type
        self.fetched: list[str] = []

    def items(self):
        for key, (version, _) in self.data.items():
            yield SourceItem(key=key, version=version, name=key.rsplit("/", 1)[-1], uri=f"fake://{key}",
                             content_type=self.content_type, metadata={"k": key})

    def fetch(self, item):
        self.fetched.append(item.key)
        body = self.data[item.key][1]
        if body is None:
            raise OSError("gone")
        return body


@pytest.fixture
def lake(tmp_path):
    return LocalStore(tmp_path)


def test_a_new_item_is_stored_with_its_meta(lake):
    stats, rows = ingest(lake, SOURCE, FakeSource({"a.txt": ("v1", b"hello")}))
    digest = layout.sha256(b"hello")
    assert stats.as_dict() == {"listed": 1, "skipped": 0, "stored": 1, "duplicate": 0, "failed": 0}
    assert rows == [{"source": "docs", "key": "a.txt", "doc_id": digest, "status": "stored"}]
    assert lake.get(layout.bronze_content_key("docs", digest, ".txt")) == b"hello"
    meta = json.loads(lake.get(layout.bronze_meta_key("docs", digest)))
    assert meta["doc_id"] == digest and meta["scope"] == "private" and meta["source_keys"] == ["a.txt"]
    assert meta["bytes"] == 5 and meta["metadata"] == {"k": "a.txt"} and meta["source_version"] == "v1"


def test_an_unchanged_item_is_skipped_without_being_read(lake):
    ingest(lake, SOURCE, FakeSource({"a.txt": ("v1", b"hello")}))
    src = FakeSource({"a.txt": ("v1", b"hello")})
    stats, rows = ingest(lake, SOURCE, src)
    assert stats.skipped == 1 and stats.stored == 0 and rows == [] and src.fetched == []


def test_a_new_version_is_read_again(lake):
    ingest(lake, SOURCE, FakeSource({"a.txt": ("v1", b"hello")}))
    stats, _ = ingest(lake, SOURCE, FakeSource({"a.txt": ("v2", b"hello again")}))
    assert stats.stored == 1


def test_an_item_with_no_version_is_always_fetched(lake):
    ingest(lake, SOURCE, FakeSource({"a.txt": ("", b"hello")}))
    src = FakeSource({"a.txt": ("", b"hello")})
    stats, rows = ingest(lake, SOURCE, src)
    assert src.fetched == ["a.txt"] and stats.duplicate == 1 and rows[0]["status"] == "duplicate"


def test_the_same_bytes_under_two_names_are_one_object_that_knows_both_names(lake):
    stats, _ = ingest(lake, SOURCE, FakeSource({"a.txt": ("1", b"same"), "b/c.txt": ("1", b"same")}))
    assert stats.stored == 1 and stats.duplicate == 1
    meta = json.loads(lake.get(layout.bronze_meta_key("docs", layout.sha256(b"same"))))
    assert meta["source_keys"] == ["a.txt", "b/c.txt"]


def test_a_failed_fetch_is_recorded_and_the_rest_continue(lake):
    stats, rows = ingest(lake, SOURCE, FakeSource({"bad.txt": ("1", None), "good.txt": ("1", b"ok")}))
    assert stats.failed == 1 and stats.stored == 1
    assert rows[0]["status"] == "fetch_failed" and "gone" in rows[0]["error"]


def test_the_limit_counts_stored_and_duplicate_items(lake):
    stats, _ = ingest(lake, SOURCE, FakeSource({f"{i}.txt": ("1", f"x{i}".encode()) for i in range(5)}), limit=2)
    assert stats.stored == 2 and stats.listed == 2


def test_bronze_objects_lists_every_object_with_its_content_key(lake):
    ingest(lake, SOURCE, FakeSource({"a.txt": ("1", b"one"), "b.txt": ("1", b"two")}))
    objs = bronze_objects(lake)
    assert set(objs) == {layout.sha256(b"one"), layout.sha256(b"two")}
    for meta in objs.values():
        assert lake.exists(meta["content_key"])


def test_bronze_objects_keeps_the_first_source_for_a_duplicate(lake):
    ingest(lake, SourceConfig("first", "fake"), FakeSource({"a.txt": ("1", b"dup")}))
    ingest(lake, SourceConfig("second", "fake"), FakeSource({"a.txt": ("1", b"dup")}))
    assert bronze_objects(lake)[layout.sha256(b"dup")]["source"] == "first"


def test_stats_start_at_zero():
    assert IngestStats().as_dict() == {"listed": 0, "skipped": 0, "stored": 0, "duplicate": 0, "failed": 0}
