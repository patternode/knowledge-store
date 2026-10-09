"""Regressions for the table lookup review: what each fix stops from happening again.

Each test names the failure it guards against: a figure checked against another figure, a
grouped figure that could never be cited, values the file writes as "1,100" or "14 July 2023",
a mapped column added after the first bind, a private table's metadata, keys with commas, and
the smaller edges (headers, key filters, empty rows, scope changes, limits).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from knowledge_store.config import SourceConfig
from knowledge_store.ontology import versions
from knowledge_store.pipeline.ingest import ingest_source
from knowledge_store.structured.bind import bind, binding, key_text
from knowledge_store.structured.query import aggregate, describe, lookup_rows, values_equal
from knowledge_store.tools import gateway
from test_structured import CORPUS, ONTO, _collection, _copy, _edit, _set_version

pydantic = pytest.importorskip("pydantic")

from knowledge_store.agent import app as agent_app  # noqa: E402
from knowledge_store.agent.grounding import Citation, Claim, FilterRef, GroundedAnswer, check, figure_matches  # noqa: E402


class Tools:
    def __init__(self, root):
        self.root, self.calls = root, []

    def call(self, name, args):
        self.calls.append((name, dict(args)))
        return gateway.call(self.root, name, args)


def _tables(tmp: Path) -> Path:
    dest = tmp / "corpus"
    shutil.copytree(CORPUS / "tables", dest / "tables")
    return dest


def _bound(tmp: Path, *, onto: Path = ONTO, corpus: Path | None = None):
    root, lake = _collection(tmp)
    versions.publish(lake, onto, by="test", activate=True)
    ingest_source(lake, SourceConfig("missions-tables", "local_dir",
                                     {"path": str(corpus or CORPUS), "pattern": "tables/*.csv"}))
    report = bind(lake)
    return root, lake, report


def _answer(*citations, text="A claim."):
    return GroundedAnswer(answerable=True, claims=[Claim(text=text, citations=list(citations))])


ATLAS = [{"attribute": "vehicleFamily", "op": "eq", "value": "Atlas V"}]


# --- a figure is checked against its own computation ---------------------------------------------

def test_two_totals_over_one_snapshot_have_two_ids(tmp_path):
    _, lake, _ = _bound(tmp_path)
    atlas = aggregate(lake, type_name="Mission", op="sum", attribute="sampleCostMillionUsd", filters=ATLAS)
    every = aggregate(lake, type_name="Mission", op="sum", attribute="sampleCostMillionUsd")
    assert atlas["snapshot"] == every["snapshot"] and atlas["id"] != every["id"]
    assert atlas["id"].startswith("m:sum:") and atlas["figure"] != every["figure"]
    # the same request gives the same id, whatever order the filters come in
    again = aggregate(lake, type_name="Mission", op="sum", attribute="sampleCostMillionUsd",
                      filters=[dict(reversed(list(ATLAS[0].items())))])
    assert again["id"] == atlas["id"]


def test_a_wrong_total_cannot_borrow_another_citations_figure(tmp_path):
    root, lake, _ = _bound(tmp_path)
    atlas = aggregate(lake, type_name="Mission", op="sum", attribute="sampleCostMillionUsd", filters=ATLAS)
    every = aggregate(lake, type_name="Mission", op="sum", attribute="sampleCostMillionUsd")
    adhoc = dict(mapped_type="Mission", attribute="sampleCostMillionUsd")
    # the reviewed failure: the Atlas V total stated as the all-missions figure, beside a true claim
    stated = GroundedAnswer(answerable=True, claims=[
        Claim(text="The Atlas V missions cost this much in total.",
              citations=[Citation(metric_id=atlas["id"], figure=str(every["figure"]),
                                  filters=[FilterRef(**f) for f in ATLAS], **adhoc)]),
        Claim(text="All missions cost this much in total.",
              citations=[Citation(metric_id=every["id"], figure=str(every["figure"]), **adhoc)])])
    kept, failures = check(stated, {}, {}, agent_app._metrics(Tools(root), "missions", stated))
    assert [c.text for c in kept] == ["All missions cost this much in total."]
    assert failures and failures[0]["reason"] == "figure does not match the snapshot"
    # and the true Atlas V claim is no longer dropped for sharing an id with the other total
    true = _answer(Citation(metric_id=atlas["id"], figure=str(atlas["figure"]),
                            filters=[FilterRef(**f) for f in ATLAS], **adhoc),
                   Citation(metric_id=every["id"], figure=str(every["figure"]), **adhoc))
    assert check(true, {}, {}, agent_app._metrics(Tools(root), "missions", true))[1] == []


def test_a_citation_whose_filters_do_not_match_its_id_is_refused(tmp_path):
    root, lake, _ = _bound(tmp_path)
    atlas = aggregate(lake, type_name="Mission", op="sum", attribute="sampleCostMillionUsd", filters=ATLAS)
    every = aggregate(lake, type_name="Mission", op="sum", attribute="sampleCostMillionUsd")
    # the unfiltered figure, under the filtered figure's id: the recomputation is not that id
    lying = _answer(Citation(metric_id=atlas["id"], figure=str(every["figure"]), mapped_type="Mission",
                             attribute="sampleCostMillionUsd"))
    kept, failures = check(lying, {}, {}, agent_app._metrics(Tools(root), "missions", lying))
    assert not kept and "do not match the id" in failures[0]["reason"]
    # an old-style id with no digest says nothing of what it was computed over
    bare = _answer(Citation(metric_id=f"m:sum/{atlas['snapshot']}", figure=str(atlas["figure"]),
                            mapped_type="Mission", attribute="sampleCostMillionUsd"))
    assert not check(bare, {}, {}, agent_app._metrics(Tools(root), "missions", bare))[0]


def test_one_group_of_a_grouped_figure_can_be_cited(tmp_path):
    root, lake, _ = _bound(tmp_path)
    grouped = aggregate(lake, type_name="Mission", op="count", group_by="vehicleFamily")
    atlas = next(g for g in grouped["groups"] if g["group"] == "Atlas V")
    assert atlas["figure"] == 5
    cite = dict(metric_id=grouped["id"], mapped_type="Mission", group_by="vehicleFamily", group="Atlas V")
    good = _answer(Citation(figure="5", **cite), text="Five missions launched on an Atlas V.")
    metrics = agent_app._metrics(Tools(root), "missions", good)
    kept, failures = check(good, {}, {}, metrics)
    assert kept and not failures
    shown = agent_app.grounding.render(kept, {}, [], {}, metrics)
    assert shown["sources"][0]["kind"] == "metric" and "Atlas V" in shown["sources"][0]["title"]
    wrong = _answer(Citation(figure="18", **cite))
    assert not check(wrong, {}, {}, agent_app._metrics(Tools(root), "missions", wrong))[0]
    missing = _answer(Citation(figure="5", **{**cite, "group": "Saturn V"}))
    kept, failures = check(missing, {}, {}, agent_app._metrics(Tools(root), "missions", missing))
    assert not kept and "no group" in failures[0]["reason"]


def test_figures_are_recomputed_once_and_capped(tmp_path):
    root, lake, _ = _bound(tmp_path)
    fig = aggregate(lake, metric="atlas_v_launches")
    tools = Tools(root)
    many = _answer(*[Citation(metric_id=fig["id"], figure="5") for _ in range(5)])
    agent_app._metrics(tools, "missions", many)
    assert sum(1 for name, _ in tools.calls if name == "aggregate") == 1


def test_stated_figures_may_use_thousands_separators_and_a_rounded_average():
    assert figure_matches("7,800", 7800) and figure_matches("$7,800", "7800")
    assert figure_matches("1234.57", "1234.5666", "avg") and figure_matches("1235", "1234.5", "avg")
    assert not figure_matches("1234.57", "1234.5666", "sum")
    assert figure_matches("1234.6", "1234.5666", "avg") and not figure_matches("1234.7", "1234.5666", "avg")
    assert not figure_matches("x", 5)
    assert FilterRef(attribute="a", value=500).value == "500"
    assert Citation(cell_id="c:x", value=1100).value == "1100"


# --- values the file writes its own way -----------------------------------------------------------

def test_numbers_and_dates_written_their_own_way_are_read_as_values(tmp_path):
    corpus = _tables(tmp_path)
    _edit(corpus / "tables/missions.csv", "2020-07-30,Mars,2700", '"30 July 2020",Mars,"2,700"')
    _edit(corpus / "tables/missions.csv", "2023-07-14,Moon,90", "2023-07-14,Moon,$90")
    root, lake, report = _bound(tmp_path, corpus=corpus)
    assert report["misses"] == []
    every = aggregate(lake, type_name="Mission", op="sum", attribute="sampleCostMillionUsd")
    assert isinstance(every["figure"], int) and "skipped" not in every
    big = lookup_rows(lake, "Mission", [{"attribute": "sampleCostMillionUsd", "op": "gt", "value": "2,000"}])
    assert "Perseverance" in {r["values"]["name"]["value"] for r in big["rows"]}
    dated = lookup_rows(lake, "Mission", [{"attribute": "launchDate", "op": "eq", "value": "2020-07-30"}])
    assert [r["values"]["name"]["value"] for r in dated["rows"]] == ["Perseverance"]
    cost = dated["rows"][0]["values"]["sampleCostMillionUsd"]
    cell = lookup_rows(lake, "", cell_ids=[cost["cell"]])["cells"][0]
    assert cell["value"] == "2700"   # stored canonical
    assert values_equal("2,700", cell["value"], "integer") and values_equal("14 July 2023", "2023-07-14", "date")
    assert not values_equal("2,701", cell["value"], "integer")


def test_a_value_that_is_not_its_type_is_skipped_never_summed_and_never_cited(tmp_path):
    corpus = _tables(tmp_path)
    _edit(corpus / "tables/missions.csv", "2023-07-14,Moon,90", "2023-07-14,Moon,ninety")
    root, lake, report = _bound(tmp_path, corpus=corpus)
    assert any(m.get("column") == "sample_cost_million_usd" for m in report["misses"])
    total = aggregate(lake, type_name="Mission", op="sum", attribute="sampleCostMillionUsd")
    assert total["skipped"] == 1 and total["figure"] is not None
    row = lookup_rows(lake, "Mission", [{"attribute": "name", "op": "eq", "value": "Chandrayaan-3"}])["rows"][0]
    bad = row["values"]["sampleCostMillionUsd"]
    cell = lookup_rows(lake, "", cell_ids=[bad["cell"]])["cells"]
    kept, failures = check(_answer(Citation(cell_id=bad["cell"], value="ninety")), {}, {bad["cell"]: {**cell[0], "invalid": True}})
    assert not kept and "valid value" in failures[0]["reason"]


# --- rebinding, keys and scope ---------------------------------------------------------------------

def test_a_column_mapped_in_a_later_version_gets_its_cells(tmp_path):
    root, lake = _collection(tmp_path)
    base = _copy(tmp_path / "base")
    _edit(base / "mappings.yaml", "      target: {attribute: target}\n", "")
    versions.publish(lake, base, by="test", activate=True)
    ingest_source(lake, SourceConfig("missions-tables", "local_dir",
                                     {"path": str(CORPUS), "pattern": "tables/*.csv"}))
    bind(lake)
    assert lookup_rows(lake, "Mission", [{"attribute": "target", "op": "eq", "value": "Mars"}]).get("total", 0) == 0
    added = tmp_path / "added"
    shutil.copytree(ONTO, added)
    _set_version(added, "1.1.0")
    assert versions.publish(lake, added, by="test", activate=True)["kind"] == "additive"
    report = bind(lake)
    assert report["written"] >= 1
    assert lookup_rows(lake, "Mission", [{"attribute": "target", "op": "eq", "value": "Mars"}])["total"] >= 2
    assert bind(lake)["written"] == 0   # and then it is unchanged


def test_keys_with_commas_stay_distinct(tmp_path):
    corpus = _tables(tmp_path)
    _edit(corpus / "tables/missions.csv", "chandrayaan-3,", '"lunar,1",')
    _edit(corpus / "tables/missions.csv", "tianwen-1,", '"lunar,2",')
    _, lake, report = _bound(tmp_path, corpus=corpus)
    rows = lookup_rows(lake, "Mission", [{"attribute": "mission_id", "op": "prefix", "value": "lunar"}])["rows"]
    assert sorted(r["key"] for r in rows) == ["lunar,1", "lunar,2"]
    assert key_text(("a,b", "c")) == "a%2Cb,c" and key_text(("a", "b,c")) == "a,b%2Cc"


def test_the_key_column_can_be_filtered_and_every_row_is_counted(tmp_path):
    corpus = _tables(tmp_path)
    # a row whose mapped columns are all empty is still a row
    (corpus / "tables/missions.csv").write_text((corpus / "tables/missions.csv").read_text() + "ghost,,,,,,,\n")
    _, lake, _ = _bound(tmp_path, corpus=corpus)
    juno = lookup_rows(lake, "Mission", [{"attribute": "mission_id", "op": "eq", "value": "juno"}])
    assert juno["total"] == 1
    count = aggregate(lake, type_name="Mission", op="count")["figure"]
    assert count == 19   # 18 missions and the ghost


def test_a_header_named_twice_is_not_bound(tmp_path):
    corpus = _tables(tmp_path)
    _edit(corpus / "tables/launch_vehicles.csv", "vehicle_id,name,family", "vehicle_id,name,name")
    _, lake, report = _bound(tmp_path, corpus=corpus)
    assert any("more than one column named name" in m.get("reason", "") for m in report["missing"])
    assert "launch_vehicles" not in binding(lake)


def test_a_header_with_spaces_still_matches(tmp_path):
    corpus = _tables(tmp_path)
    _edit(corpus / "tables/launch_vehicles.csv", "vehicle_id,name,family", " vehicle_id , name ,family")
    _, lake, _ = _bound(tmp_path, corpus=corpus)
    assert lookup_rows(lake, "LaunchVehicle", [{"attribute": "vehicleId", "op": "eq", "value": "lvm3"}])["total"] == 1


def test_a_table_made_private_after_the_first_bind_is_rebound_private(tmp_path):
    root, lake = _collection(tmp_path)
    versions.publish(lake, ONTO, by="test", activate=True)
    ingest_source(lake, SourceConfig("missions-tables", "local_dir",
                                     {"path": str(CORPUS), "pattern": "tables/*.csv"}))
    bind(lake)
    assert lookup_rows(lake, "LaunchVehicle")["total"] > 0
    private = _copy(tmp_path / "private")
    _edit(private / "mappings.yaml", "class: LaunchVehicle\n    key:", "class: LaunchVehicle\n    scope: private\n    key:")
    _set_version(private, "2.0.0")
    versions.publish(lake, private, by="test", activate=True)
    bind(lake)
    assert lookup_rows(lake, "LaunchVehicle")["total"] == 0
    assert lookup_rows(lake, "LaunchVehicle", private=True)["total"] > 0


def test_a_held_snapshot_stands_only_for_the_same_file_mapping_and_scope(tmp_path):
    from knowledge_store.structured.bind import _unchanged, mapping_hash, published_mapping
    _, lake, _ = _bound(tmp_path)
    table = published_mapping(lake).table("missions")
    held = binding(lake)["missions"]
    meta = {"scope": "public"}
    assert _unchanged(lake, held, table, meta, held["snapshot"])
    assert not _unchanged(lake, held, table, {"scope": "private"}, held["snapshot"])   # the source went private
    assert not _unchanged(lake, {**held, "mapping": "0" * 16}, table, meta, held["snapshot"])
    assert not _unchanged(lake, {k: v for k, v in held.items() if k != "mapping"}, table, meta, held["snapshot"])
    assert not _unchanged(lake, held, table, meta, "another-file")
    assert held["mapping"] == mapping_hash(table)


# --- scope and inputs at the tools -----------------------------------------------------------------

def test_a_private_table_is_not_described_to_a_public_caller(tmp_path):
    root, lake = _collection(tmp_path)
    dest = _copy(tmp_path)
    _edit(dest / "mappings.yaml", "class: LaunchVehicle\n    key:", "class: LaunchVehicle\n    scope: private\n    key:")
    versions.publish(lake, dest, activate=True)
    ingest_source(lake, SourceConfig("missions-tables", "local_dir",
                                     {"path": str(CORPUS), "pattern": "tables/*.csv"}))
    bind(lake)
    public = gateway.call(root, "describe_structured", {"collection": "missions"})
    private = gateway.call(root, "describe_structured", {"collection": "missions", "caller_private": True})
    assert [t["type"] for t in public["types"]] == ["Mission"]
    assert {t["type"] for t in private["types"]} == {"Mission", "LaunchVehicle"}
    assert describe(lake)["types"] == public["types"]


def test_bad_tool_arguments_cost_a_tool_call_not_the_answer(tmp_path):
    from types import SimpleNamespace

    from knowledge_store.portal_api import chat
    root, lake, _ = _bound(tmp_path)
    idx = SimpleNamespace(lake=lake)
    one = chat.run_tool(idx, "lookup_rows", {"type": "Mission", "filters": {"attribute": "name", "op": "eq", "value": "Juno"},
                                             "limit": "lots"}, private=False)
    assert one["total"] == 1   # a single filter object is read as a list of one
    junk = chat.run_tool(idx, "lookup_rows", {"type": "Mission", "filters": "name = Juno"}, private=False)
    assert "rows" in junk
    broken = chat.run_tool(idx, "get_entity", {"id": "x"}, private=False)   # this idx has no graph
    assert "error" in broken
    assert gateway.call(root, "lookup_rows", {"collection": "missions", "type": "Mission", "limit": "x"})["rows"]


def test_the_portal_shows_only_figures_a_tool_returned(tmp_path):
    from types import SimpleNamespace

    from knowledge_store.portal_api import chat
    _, lake, _ = _bound(tmp_path)
    idx = SimpleNamespace(lake=lake, passages={}, visible=lambda *_: True)
    fig = aggregate(lake, metric="atlas_v_launches")
    made_up = chat.cited(idx, "Five. [m:m:anything/123]", private=False, figures={})
    assert made_up == []
    real = chat.cited(idx, f"Five. [m:{fig['id']}]", private=False, figures={fig["id"]: fig})
    assert real[0]["kind"] == "metric" and real[0]["quotes"] == ["5"] and "atlas_v_launches" in real[0]["title"]


def test_the_cost_keeps_calls_the_hooks_did_not_see():
    from knowledge_store import workbench
    steps = [{"n": 1, "kind": "model", "title": "Thinking", "usage": {"inputTokens": 100, "outputTokens": 10}}]
    cost = workbench.query_cost(steps, model_id=None, usage={"inputTokens": 900, "outputTokens": 90})
    assert sum(p["tokens"] for p in cost["parts"]) == 990


def test_a_sample_link_to_a_table_opens_its_snapshot_in_scope(tmp_path):
    from knowledge_store.portal_api import handler
    root, lake = _collection(tmp_path)
    dest = _copy(tmp_path)
    _edit(dest / "mappings.yaml", "class: LaunchVehicle\n    key:", "class: LaunchVehicle\n    scope: private\n    key:")
    versions.publish(lake, dest, activate=True)
    ingest_source(lake, SourceConfig("missions-tables", "local_dir",
                                     {"path": str(CORPUS), "pattern": "tables/*.csv"}))
    bind(lake)
    assert handler.table_link(lake, "tables/missions.csv", private=False)["name"] == "missions.csv"
    assert handler.table_link(lake, "tables/launch_vehicles.csv", private=False) is None
    assert handler.table_link(lake, "tables/launch_vehicles.csv", private=True)["name"] == "launch_vehicles.csv"
    assert handler.table_link(lake, "tables/nothing.csv", private=True) is None
