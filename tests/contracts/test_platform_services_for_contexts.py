"""What every context relies on from Platform services' contract: the Store, JSON helpers, the
layout, the profile and sources, collections, the ledger and model helpers. One file, one
section per consumer, since all of them use the same few names."""

from __future__ import annotations

import pytest

from contract_support import published
from knowledge_store import platform_services as ps

USES = {
    "ingestion": ["S3Store", "SourceConfig", "Store", "layout", "put_json"],
    "ontology": ["Profile", "Store", "decode_tool_input", "layout", "put_json"],
    "extraction": ["Profile", "Store", "layout", "ledger", "put_json"],
    "knowledge_graph": ["S3Store", "Store", "collections", "get_json", "layout", "load_profile", "load_sources", "put_json"],
    "answering": ["layout", "ledger", "llm", "strands_model"],
    "evaluation": ["store_from_uri"],
}


@pytest.mark.parametrize("consumer", sorted(USES))
def test_each_consumer_finds_what_it_uses(consumer):
    published("platform_services", USES[consumer])


def test_a_store_from_a_path_reads_back_what_it_wrote(tmp_path):
    s = ps.store_from_uri(str(tmp_path))
    ps.put_json(s, "a/b.json", {"x": 1})
    assert s.exists("a/b.json") and ps.get_json(s, "a/b.json") == {"x": 1} and list(s.list("a/")) == ["a/b.json"]
    assert s.put_if_absent("a/c", b"1") and not s.put_if_absent("a/c", b"2")
    s.delete("a/c")
    assert not s.exists("a/c") and s.uri("a/b.json").endswith("a/b.json")


def test_a_collection_is_a_store_under_its_own_prefix(tmp_path):
    root = ps.store_from_uri(str(tmp_path))
    lake = ps.collections.scoped(root, "m")
    ps.put_json(lake, "status.json", {})
    assert root.exists("collections/m/status.json") and list(lake.list("")) == ["status.json"]


def test_the_layout_names_the_keys_contexts_share():
    for name in ("STATUS", "CONFIG_SETTINGS", "CONFIG_SOURCES", "CONFIG_PROFILE", "PIPELINE_LOCK", "ONTOLOGY_DRAFTS",
                 "SILVER_DOCS", "BRONZE", "SEEN", "TERM_REQUESTS"):
        assert isinstance(getattr(ps.layout, name), str), name
    assert ps.layout.doc_id_from_key(ps.layout.doc_key("d1")) == "d1"


def test_a_profile_with_nothing_configured_still_loads(tmp_path):
    p = ps.load_profile(ps.store_from_uri(str(tmp_path)))
    assert isinstance(p, ps.Profile) and isinstance(p.sample_questions(), list)
    sources = ps.load_sources(ps.store_from_uri(str(tmp_path)))
    assert [(s.name, s.type, s.scope) for s in sources] == [("uploads", "s3_landing", "public")]


def test_a_tool_input_decodes_json_strings_where_the_schema_wants_structure():
    schema = {"type": "object", "properties": {"items": {"type": "array"}, "n": {"type": "integer"}}}
    assert ps.decode_tool_input({"items": '["a", "b"]', "n": 1}, schema) == {"items": ["a", "b"], "n": 1}
    assert ps.decode_tool_input({"items": "not json"}, schema) == {"items": "not json"}


def test_the_ledger_prices_a_call_in_parts():
    assert callable(ps.ledger.cost_parts)


def test_the_model_helpers_name_their_provider():
    assert callable(ps.llm.provider) and isinstance(ps.llm.ANTHROPIC, str)
