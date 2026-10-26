"""The Gateway's Lambda targets: fixed tools over the knowledge graph and passages, scope from the
interceptor, failures returned as data. The lake is a local folder holding a hand-written projection
(no NEPTUNE_ENDPOINT, no KNOWLEDGE_BASE_ID), so every tool answers from memory."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from knowledge_store.knowledge_graph.adapters import gateway, index
from knowledge_store.platform_services.adapters.store import LocalStore
from knowledge_store.platform_services.ports import put_json
from knowledge_store.platform_services.slices import collections
from kg_projection import ALPHA, NOVA, ZETA, write


@pytest.fixture
def root(tmp_path, monkeypatch):
    for v in ("NEPTUNE_ENDPOINT", "KNOWLEDGE_BASE_ID", "TOOLSET"):
        monkeypatch.delenv(v, raising=False)
    r = LocalStore(tmp_path / "root")
    put_json(r, collections.CONFIG, [{"id": "m"}, {"id": "empty"}])
    write(collections.scoped(r, "m"))
    monkeypatch.setattr(gateway, "_lake", r)
    index._cache.clear()
    return r


def ctx(tool):
    return SimpleNamespace(client_context=SimpleNamespace(custom={"bedrockAgentCoreToolName": f"target___{tool}"}))


def test_every_tool_schema_declares_caller_private():
    for t in gateway.tool_schema():
        assert "caller_private" in t["inputSchema"]["properties"] and t["inputSchema"]["type"] == "object"


def test_the_toolsets_split_graph_passages_and_the_walk():
    graph = {t["name"] for t in gateway.tool_schema("graph")}
    passage = {t["name"] for t in gateway.tool_schema("passages")}
    walk = {t["name"] for t in gateway.tool_schema("walk")}
    assert passage == {"search_passages", "read_passages"} and not graph & passage
    assert walk == passage | {"related_passages"} and not graph & walk
    assert graph | walk == {t["name"] for t in gateway.tool_schema("all")}


def test_the_tool_name_comes_from_the_gateways_context():
    assert gateway.tool_name(ctx("get_entity")) == "get_entity"
    assert gateway.tool_name(None) == "" and gateway.tool_name(SimpleNamespace(client_context=None)) == ""


def test_list_collections_names_each_with_its_ontology_version(root):
    out = gateway.call(root, "list_collections", {})
    assert {c["id"]: c["ontology_version"] for c in out["collections"]} == {"m": "1.0.0", "empty": None}


def test_an_unknown_collection_points_to_list_collections(root):
    assert "list_collections" in gateway.call(root, "get_entity", {"collection": "nope"})["error"]


def test_a_collection_without_a_released_ontology_says_so(root):
    assert "no released ontology" in gateway.call(root, "describe_ontology", {"collection": "empty"})["error"]
    assert "no knowledge graph yet" in gateway.call(root, "get_entity", {"collection": "empty", "id": ALPHA})["error"]


def test_without_the_interceptor_a_caller_is_public(root):
    assert "no entity" in gateway.call(root, "get_entity", {"collection": "m", "id": ZETA})["error"]
    assert gateway.call(root, "get_entity", {"collection": "m", "id": ZETA, "caller_private": True})["id"] == ZETA


def test_only_a_boolean_true_is_private(root):
    assert "error" in gateway.call(root, "get_entity", {"collection": "m", "id": ZETA, "caller_private": "true"})


def test_entity_tools_carry_the_ontology_version(root):
    out = gateway.call(root, "search_entities", {"collection": "m", "query": "Nova"})
    assert out["ontology_version"] == "1.0.0" and [i["id"] for i in out["items"]] == [NOVA]


def test_neighbourhood_and_paths_are_in_scope(root):
    hood = gateway.call(root, "neighbourhood", {"collection": "m", "id": NOVA, "limit": 500})
    assert {n["id"] for n in hood["nodes"]} == {NOVA, ALPHA}
    assert gateway.call(root, "find_paths", {"collection": "m", "from": ALPHA, "to": ZETA})["paths"] == []
    assert gateway.call(root, "find_paths", {"collection": "m", "from": ALPHA, "to": ZETA, "caller_private": True})["hops"] == 2


def test_passage_tools_search_by_keyword_and_read_in_scope(root):
    found = gateway.call(root, "search_passages", {"collection": "m", "query": "launched", "limit": 50})
    assert found["method"] == "keyword" and [p["id"] for p in found["passages"]] == ["p-pub"]
    read = gateway.call(root, "read_passages", {"collection": "m", "ids": ["p-pub", "p-priv"]})
    assert [p["id"] for p in read["passages"]] == ["p-pub"]


def test_the_structured_tools_answer_without_mapped_tables(root):
    assert gateway.call(root, "describe_structured", {"collection": "m"}) == {"types": [], "metrics": []}
    assert "error" in gateway.call(root, "lookup_rows", {"collection": "m", "type": "Mission"})
    assert "error" in gateway.call(root, "aggregate", {"collection": "m", "metric": "x"})


def test_the_handler_refuses_a_tool_outside_its_toolset(root, monkeypatch):
    monkeypatch.setenv("TOOLSET", "passages")
    assert gateway.lambda_handler({"collection": "m", "id": ALPHA}, ctx("get_entity")) == {"error": "unknown tool 'get_entity'"}


def test_the_handler_takes_the_tool_from_the_event_without_a_gateway_context(root):
    out = gateway.lambda_handler({"__tool": "list_collections"}, None)
    assert {c["id"] for c in out["collections"]} == {"m", "empty"}


def test_a_tool_failure_is_returned_as_data(root, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("the store is down")

    monkeypatch.setattr(gateway, "call", boom)
    assert gateway.lambda_handler({"collection": "m"}, ctx("get_entity")) == {"error": "the store is down"}


def test_the_lake_is_the_bucket_named_in_the_environment(monkeypatch):
    made = []
    monkeypatch.setattr(gateway, "_lake", None)
    monkeypatch.setattr(gateway, "S3Store", lambda bucket: made.append(bucket) or f"s3:{bucket}")
    monkeypatch.setenv("LAKE_BUCKET", "lake-bucket")
    assert gateway.lake() == gateway.lake() == "s3:lake-bucket" and made == ["lake-bucket"]


def test_with_neptune_configured_the_graph_index_reads_the_store(root, monkeypatch):
    seen = []
    from knowledge_store.knowledge_graph.adapters import sparql
    monkeypatch.setattr(sparql, "client_from_env", lambda: "client")
    monkeypatch.setattr(sparql, "load", lambda store, cid, client: seen.append((cid, client)) or None)
    assert "no knowledge graph yet" in gateway.call(root, "get_entity", {"collection": "m", "id": ALPHA})["error"]
    assert seen == [("m", "client")]


def test_describe_ontology_returns_the_agent_rendition(root):
    from knowledge_store.platform_services.domain import layout
    lake = collections.scoped(root, "m")
    lake.put(f"{layout.ontology_version_prefix('1.0.0')}/renditions/agent/ontology.md", b"# Missions\n")
    assert gateway.call(root, "describe_ontology", {"collection": "m"}) == {"collection": "m", "version": "1.0.0",
                                                                           "ontology": "# Missions\n"}
