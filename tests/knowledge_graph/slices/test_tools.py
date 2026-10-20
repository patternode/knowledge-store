"""The read tools: one implementation for every surface, scope-filtered, failures as data."""

from __future__ import annotations

import pytest

from knowledge_store.knowledge_graph.slices import tools
from kg_projection import ALPHA, NOVA, ZETA, index_of


@pytest.fixture
def idx(tmp_path):
    return index_of(tmp_path)


def test_every_tool_has_a_spec_with_its_required_inputs():
    specs = {s["toolSpec"]["name"]: s["toolSpec"] for s in tools.tool_config()["tools"]}
    assert set(specs) == {t["name"] for t in tools.TOOLS}
    for t in tools.TOOLS:
        schema = specs[t["name"]]["inputSchema"]["json"]
        assert schema["type"] == "object" and schema["required"] == t["required"]


def test_the_filter_reference_is_inlined_in_the_tool_specs():
    specs = {s["toolSpec"]["name"]: s["toolSpec"] for s in tools.tool_config()["tools"]}
    items = specs["lookup_rows"]["inputSchema"]["json"]["properties"]["filters"]["items"]
    assert items == tools.FILTER and "$ref" not in str(specs)


def test_the_vocabulary_lists_types_relations_and_attributes(idx):
    text = tools.vocabulary(idx)
    assert "- type SpaceAgency (a kind of Organisation): An agency. [1 in graph]" in text
    assert "- relation launchedBy: Mission -> SpaceAgency: Who launched it." in text
    assert "- relation relatedTo: any -> any: Anything." in text
    assert "- attribute launchYear of Mission (integer): The year." in text


def test_the_vocabulary_counts_everything_for_a_private_caller(idx):
    assert "- type Mission: A mission. [2 in graph]" in tools.vocabulary(idx, private=True)


def test_the_profile_text_names_the_collection_and_its_key_terms(idx):
    assert tools.profile_text(idx) == "Collection: Missions\nSpace missions.\nKey terms: mission, agency"


def test_the_profile_text_without_key_terms(idx):
    idx.summary["profile"].pop("key_terms")
    assert tools.profile_text(idx) == "Collection: Missions\nSpace missions."


def test_search_entities_finds_by_name_in_scope(idx):
    assert [i["id"] for i in tools.run_tool(idx, "search_entities", {"query": "Mission"}, False)["items"]] == [ALPHA]
    found = tools.run_tool(idx, "search_entities", {"query": "Mission"}, True)["items"]
    assert {i["id"] for i in found} == {ALPHA, ZETA}


def test_search_entities_never_matches_a_private_alias_for_a_public_caller(idx):
    assert tools.run_tool(idx, "search_entities", {"query": "Hush"}, False)["total"] == 0
    assert tools.run_tool(idx, "search_entities", {"query": "Hush"}, True)["total"] == 1


def test_list_entities_lists_one_type(idx):
    assert [i["id"] for i in tools.run_tool(idx, "list_entities", {"type": "SpaceAgency"}, False)["items"]] == [NOVA]


def test_a_bad_limit_falls_back_to_the_default(idx):
    assert tools.run_tool(idx, "search_entities", {"query": "Mission", "limit": "many"}, True)["total"] == 2


def test_get_entity_labels_its_relations(idx):
    e = tools.run_tool(idx, "get_entity", {"id": ALPHA}, False)
    assert e["out"] == [{"p": "launchedBy", "o": NOVA, "passages": ["p-pub"], "o_label": "Agency Nova"}]


def test_get_entity_hides_private_relations_from_a_public_caller(idx):
    nova = tools.run_tool(idx, "get_entity", {"id": NOVA}, False)
    assert [r["s"] for r in nova["in"]] == [ALPHA] and nova["aliases"] == ["Nova"]
    nova = tools.run_tool(idx, "get_entity", {"id": NOVA}, True)
    assert {r["s"]: r["s_label"] for r in nova["in"]} == {ALPHA: "Mission Alpha", ZETA: "Mission Zeta"}


def test_get_entity_refuses_a_private_or_unknown_entity_to_a_public_caller(idx):
    assert "no entity" in tools.run_tool(idx, "get_entity", {"id": ZETA}, False)["error"]
    assert "no entity" in tools.run_tool(idx, "get_entity", {"id": "nope"}, True)["error"]


def test_search_passages_is_in_scope(idx):
    assert [p["id"] for p in tools.run_tool(idx, "search_passages", {"query": "launched"}, False)["passages"]] == ["p-pub"]
    assert len(tools.run_tool(idx, "search_passages", {"query": "launched"}, True)["passages"]) == 2


def test_read_passages_returns_only_known_passages_in_scope(idx):
    out = tools.run_tool(idx, "read_passages", {"ids": ["p-pub", "p-priv", "nope"]}, False)["passages"]
    assert [p["id"] for p in out] == ["p-pub"] and out[0]["text"].startswith("Mission Alpha")


def test_the_structured_tools_answer_without_mapped_tables(idx):
    assert tools.run_tool(idx, "describe_structured", {}, False) == {"types": [], "metrics": []}
    assert "no mapped tables" in tools.run_tool(idx, "lookup_rows", {"type": "Mission"}, False)["error"]
    assert "no mapped tables" in tools.run_tool(idx, "aggregate", {"metric": "x"}, False)["error"]


def test_an_unknown_tool_is_an_error(idx):
    assert tools.run_tool(idx, "drop_everything", {}, True) == {"error": "unknown tool drop_everything"}


def test_arguments_that_are_not_a_dict_are_treated_as_none(idx):
    assert tools.run_tool(idx, "search_entities", ["Mission"], True)["total"] == 3


def test_a_failure_goes_back_as_data(idx):
    out = tools.run_tool(idx, "read_passages", {"ids": 7}, True)
    assert out["error"].startswith("read_passages failed: TypeError")
