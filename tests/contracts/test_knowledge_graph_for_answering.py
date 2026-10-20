"""What Answering relies on from the Knowledge graph's contract: the read tools, the index, the
table queries' descriptions and comparisons, and the gateway's tool list."""

from __future__ import annotations

from contract_support import published
from knowledge_store import knowledge_graph as kg

USES = ["FILTER", "Index", "TOOLS", "describe", "describe_figure", "gateway", "profile_text", "run_tool", "table_query",
        "tool_config", "values_equal", "vocabulary"]


def test_answering_finds_what_it_uses():
    published("knowledge_graph", USES)


def test_the_tools_have_names_descriptions_and_inputs():
    assert kg.TOOLS and all({"name", "description", "input"} <= set(t) for t in kg.TOOLS)
    assert len({t["name"] for t in kg.TOOLS}) == len(kg.TOOLS)


def test_a_filter_names_an_attribute_and_a_value():
    assert kg.FILTER["type"] == "object" and set(kg.FILTER["required"]) == {"attribute", "value"}


def test_the_model_tool_config_lists_every_tool():
    cfg = kg.tool_config()
    names = {t["toolSpec"]["name"] for t in cfg["tools"]}
    assert {t["name"] for t in kg.TOOLS} <= names


def test_the_vocabulary_and_profile_read_from_the_index(swept):
    idx = kg.index.load(swept, "m")
    assert isinstance(kg.vocabulary(idx), str) and isinstance(kg.profile_text(idx), str)


def test_a_tool_runs_against_the_index(swept):
    idx = kg.index.load(swept, "m")
    out = kg.run_tool(idx, "search_entities", {"query": "Alpha"}, private=False)
    assert isinstance(out, dict)


def test_values_compare_as_their_datatype():
    assert kg.values_equal("7,800", "7800", "integer")
    assert kg.values_equal("14 July 2023", "2023-07-14", "date")
    assert not kg.values_equal("Atlas", "atlas", "string")


def test_a_figure_is_described_in_words():
    assert kg.describe_figure({"op": "count", "type": "Mission"}) == "count over Mission"
    assert kg.describe_figure({"metric": "launches", "description": "per year"}) == "launches (per year)"


def test_a_lake_without_tables_describes_no_tables(swept):
    assert isinstance(kg.describe(swept), dict)


def test_the_index_loads_for_a_swept_collection(swept):
    idx = kg.index.load(swept, "m")
    assert isinstance(idx, kg.Index) and idx.entities
