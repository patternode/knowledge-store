"""lookup_rows, aggregate and describe_structured over the space-missions catalog, bound in a
local folder lake; and the pure rules they share (filters, comparisons, figure ids, citations)."""

from __future__ import annotations

import shutil
from decimal import Decimal
from pathlib import Path

import pytest

from knowledge_store.extraction.slices.bind_tables import bind
from knowledge_store.ingestion.adapters.registry import ingest_source
from knowledge_store.knowledge_graph.slices import table_query as tq
from knowledge_store.ontology.slices import versions
from knowledge_store.platform_services.adapters.store import LocalStore
from knowledge_store.platform_services.ports import put_json
from knowledge_store.platform_services.slices import collections
from knowledge_store.platform_services.slices.config import SourceConfig

ROOT = Path(__file__).resolve().parents[3]
ONTO = ROOT / "examples/space-missions/ontology"
TABLES = ROOT / "examples/space-missions/tables"


def _metric(name: str, expression: str, table: str = "missions") -> str:
    return f"""
  - name: {name}
    description: "{name} in words."
    expression:
      dialects:
        - dialect: ANSI_SQL
          expression: "{expression}"
    custom_extensions:
      - vendor_name: COA
        data:
          source_table: {table}
          ontology_concepts: [Mission]
"""


EXTRA = [
    _metric("cheap_cost", "SELECT SUM(sample_cost_million_usd) FROM missions WHERE sample_cost_million_usd < 200"),
    _metric("mars_avg_cost", "SELECT AVG(sample_cost_million_usd) FROM missions WHERE target = 'Mars'"),
    _metric("not_atlas", "SELECT COUNT(*) FROM missions WHERE vehicle_family <> 'Atlas V'"),
    _metric("ored", "SELECT COUNT(*) FROM missions WHERE target = 'Mars' OR target = 'Moon'"),
    _metric("names", "SELECT name FROM missions"),
    _metric("elsewhere", "SELECT COUNT(*) FROM launch_vehicles"),
]


def _bound(tmp: Path, *, private_vehicles: bool = False, extra: bool = True):
    onto = tmp / "onto"
    shutil.copytree(ONTO, onto)
    if extra:
        with open(onto / "metrics.osi.yaml", "a") as f:
            f.write("".join(EXTRA))
    if private_vehicles:
        m = onto / "mappings.yaml"
        m.write_text(m.read_text().replace("class: LaunchVehicle\n    key:", "class: LaunchVehicle\n    scope: private\n    key:"))
    root = LocalStore(tmp / "root")
    put_json(root, collections.CONFIG, [{"id": "missions"}])
    lake = collections.scoped(root, "missions")
    versions.publish(lake, onto, by="test", activate=True)
    ingest_source(lake, SourceConfig("missions-tables", "local_dir", {"path": str(TABLES.parent), "pattern": "tables/*.csv"}))
    report = bind(lake)
    assert report["misses"] == [], report["misses"]
    tq._cache.clear()
    return lake


@pytest.fixture(scope="module")
def lake(tmp_path_factory):
    return _bound(tmp_path_factory.mktemp("catalog"))


@pytest.fixture(scope="module")
def hidden(tmp_path_factory):
    return _bound(tmp_path_factory.mktemp("hidden"), private_vehicles=True, extra=False)


# --- the pure rules -------------------------------------------------------------------------


def test_a_single_filter_object_is_a_list_of_one():
    assert tq.clean_filters({"attribute": "name", "value": "Juno"}) == [{"attribute": "name", "op": "eq", "value": "Juno"}]


def test_filters_that_are_not_filters_are_dropped():
    assert tq.clean_filters(["nope", 3, {"column": "name", "value": None}]) == [{"attribute": "name", "op": "eq", "value": ""}]
    assert tq.clean_filters("name = Juno") == []


def test_at_most_max_filters_are_read():
    assert len(tq.clean_filters([{"attribute": "a", "value": "1"}] * 50)) == tq.MAX_FILTERS


@pytest.mark.parametrize("op,value,expected", [("eq", "1100", True), ("eq", "1,100", True), ("neq", "1100", False),
                                               ("lt", "2000", True), ("lte", "1100", True), ("gt", "1100", False),
                                               ("gte", "1100", True)])
def test_numbers_compare_as_numbers(op, value, expected):
    assert tq._cmp(op, "1100", "integer", value) is expected


def test_a_value_that_is_not_a_number_never_matches_a_number():
    assert not tq._cmp("eq", "n/a", "integer", "1") and not tq._cmp("eq", "1", "decimal", "one")


@pytest.mark.parametrize("op,expected", [("eq", True), ("neq", False), ("lt", False), ("lte", True), ("gt", False), ("gte", True)])
def test_dates_compare_as_dates(op, expected):
    assert tq._cmp(op, "2023-07-14", "date", "14 July 2023") is expected


def test_an_unreadable_date_never_matches():
    assert not tq._cmp("eq", "someday", "date", "2023-07-14")


def test_a_duration_that_cannot_be_read_never_matches_and_not_equal_is_read():
    assert tq._cmp("eq", "PT2H", "duration", "two hours") is False
    assert tq._cmp("neq", "PT2H", "duration", "PT3H") is True
    assert tq._cmp("neq", "2023-07-14/2023-07-20", "interval", "14 July 2023/20 July 2023") is False


def test_the_cell_cache_is_emptied_once_it_holds_more_than_sixty_four_snapshots(lake):
    import time
    tq._cache.clear()
    for i in range(65):
        tq._cache[f"snapshot-{i}"] = (time.monotonic(), [])
    assert tq._read_cells(lake, "gold/no-such-snapshot.jsonl") == []
    assert len(tq._cache) == 1
    tq._cache.clear()


def test_a_date_and_time_orders_and_a_duration_only_matches():
    assert tq._cmp("lt", "2023-07-14T15:30Z", "dateTime", "2023-07-14T16:00Z")
    assert tq._cmp("eq", "PT2.0H", "duration", "PT2H")
    assert tq._cmp("lt", "PT2H", "duration", "PT10H") is False
    assert tq.values_equal("14 July 2023/20 July 2023", "2023-07-14/2023-07-20", "interval")


@pytest.mark.parametrize("op,expected", [("eq", False), ("neq", True), ("lt", True), ("lte", True), ("gt", False),
                                         ("gte", False), ("prefix", False)])
def test_text_compares_as_text(op, expected):
    assert tq._cmp(op, "Apollo", "string", "Juno") is expected


def test_prefix_matches_the_start_of_the_text():
    assert tq._cmp("prefix", "Juno", "string", "Ju")


def test_where_reads_and_joined_comparisons():
    assert tq._where("target = 'Mars' AND sample_cost_million_usd >= 100") == [
        {"attribute": "target", "op": "eq", "value": "Mars"},
        {"attribute": "sample_cost_million_usd", "op": "gte", "value": "100"}]


def test_a_where_it_cannot_recompute_is_refused():
    with pytest.raises(ValueError, match="not recomputable"):
        tq._where("target IN ('Mars')")


def test_reduce_counts_sums_and_averages():
    assert tq._reduce("count", ["a", "b"], "integer") == 2
    assert tq._reduce("sum", ["1", "2", "x"], "integer") == 3
    assert tq._reduce("min", ["3", "2"], "integer") == 2 and tq._reduce("max", ["3", "2"], "integer") == 3
    assert tq._reduce("avg", ["1", "2"], "decimal") == Decimal("1.5")
    assert tq._reduce("sum", ["x"], "integer") is None


def test_reduce_refuses_an_unknown_op():
    with pytest.raises(ValueError):
        tq._reduce("median", ["1"], "integer")


def test_figures_are_written_without_trailing_zeros():
    assert tq._figure(Decimal("1.50")) == "1.5" and tq._figure(Decimal("2.000")) == "2" and tq._figure(Decimal("7")) == "7"
    assert tq._figure(None) is None and tq._figure(5) == 5


def test_a_figure_id_names_what_it_is_the_figure_of():
    one = tq.figure_id("sum", "Mission", "cost", [{"attribute": "target", "value": "Mars"}], "", "s1")
    assert one.startswith("m:sum:") and one.endswith("/s1")
    assert one == tq.figure_id("sum", "Mission", "cost", {"attribute": "target", "value": "Mars"}, "", "s1")
    assert one != tq.figure_id("sum", "Mission", "cost", [{"attribute": "target", "value": "Moon"}], "", "s1")


def test_a_figure_is_described_in_words():
    assert tq.describe_figure({"metric": "atlas_v_launches", "description": "Atlas V missions"}) == "atlas_v_launches (Atlas V missions)"
    assert tq.describe_figure({"metric": "m"}) == "m"
    assert tq.describe_figure({"op": "sum", "attribute": "cost", "type": "Mission",
                               "filters": [{"attribute": "target", "op": "eq", "value": "Mars"}]}) == \
        "sum of cost over Mission where target eq Mars"


@pytest.mark.parametrize("stated,stored,datatype,expected", [
    ("7,800", "7800", "integer", True), ("7.8", "7800", "decimal", False), ("n/a", "1", "integer", False),
    ("14 July 2023", "2023-07-14", "date", True), ("someday", "2023-07-14", "date", False),
    (" Mars ", "Mars", "string", True), ("Moon", "Mars", "string", False)])
def test_a_cited_value_is_compared_in_its_datatype(stated, stored, datatype, expected):
    assert tq.values_equal(stated, stored, datatype) is expected


# --- describe -------------------------------------------------------------------------------


def test_describe_lists_the_bound_types_and_metrics(lake):
    d = tq.describe(lake)
    assert {t["type"] for t in d["types"]} == {"Mission", "LaunchVehicle"}
    missions = next(t for t in d["types"] if t["type"] == "Mission")
    assert missions["rows"] == 18 and missions["key"] == ["mission_id"] and missions["snapshot"]
    assert "atlas_v_launches" in {m["name"] for m in d["metrics"]} and d["version"]


def test_a_collection_without_a_mapping_has_nothing_to_describe(tmp_path):
    assert tq.describe(LocalStore(tmp_path)) == {"types": [], "metrics": []}


def test_a_private_table_and_its_metrics_are_not_described_to_a_public_caller(hidden):
    assert {t["type"] for t in tq.describe(hidden)["types"]} == {"Mission"}
    assert {t["type"] for t in tq.describe(hidden, private=True)["types"]} == {"Mission", "LaunchVehicle"}


# --- lookup_rows ----------------------------------------------------------------------------


def test_rows_are_found_by_class_or_by_table(lake):
    by_class = tq.lookup_rows(lake, "Mission", [{"attribute": "name", "op": "eq", "value": "Perseverance"}])
    by_table = tq.lookup_rows(lake, "missions", [{"attribute": "name", "op": "eq", "value": "Perseverance"}])
    assert by_class["rows"] == by_table["rows"] and by_class["total"] == 1


def test_a_row_carries_each_value_with_its_cell_id(lake):
    row = tq.lookup_rows(lake, "Mission", [{"attribute": "mission_id", "value": "perseverance"}])["rows"][0]
    assert row["key"] == "perseverance" and row["values"]["target"]["value"] == "Mars"
    assert row["values"]["target"]["cell"].endswith("/missions/perseverance/target")


def test_rows_filter_numbers_and_dates_in_their_datatype(lake):
    cheap = tq.lookup_rows(lake, "Mission", [{"attribute": "sampleCostMillionUsd", "op": "lt", "value": "100"}], limit=100)
    assert cheap["total"] and all(int(r["values"]["sampleCostMillionUsd"]["value"]) < 100 for r in cheap["rows"])
    recent = tq.lookup_rows(lake, "Mission", [{"attribute": "launchDate", "op": "gte", "value": "1 January 2020"}], limit=100)
    assert recent["total"] and all(r["values"]["launchDate"]["value"] >= "2020-01-01" for r in recent["rows"])


def test_a_filter_on_an_unknown_column_or_op_matches_nothing(lake):
    assert tq.lookup_rows(lake, "Mission", [{"attribute": "colour", "value": "red"}])["total"] == 0
    assert tq.lookup_rows(lake, "Mission", [{"attribute": "name", "op": "like", "value": "J%"}])["total"] == 0


def test_the_row_cap_truncates(lake):
    out = tq.lookup_rows(lake, "Mission", limit=3)
    assert len(out["rows"]) == 3 and out["total"] == 18 and out["truncated"]


def test_an_unknown_type_points_to_describe(lake):
    assert "describe_structured" in tq.lookup_rows(lake, "Comet")["error"]


def test_lookup_without_a_mapping_is_an_error(tmp_path):
    assert tq.lookup_rows(LocalStore(tmp_path), "Mission") == {"error": "this collection has no mapped tables"}


def test_cells_are_read_by_id_with_their_row(lake):
    cell = tq.lookup_rows(lake, "Mission", [{"attribute": "mission_id", "value": "perseverance"}])["rows"][0]["values"]["target"]["cell"]
    found = tq.lookup_rows(lake, "", cell_ids=cell)["cells"]
    assert [c["value"] for c in found] == ["Mars"] and any(r["column"] == "name" for r in found[0]["row"])


def test_a_private_table_is_not_named_to_a_public_caller(hidden):
    assert "error" in tq.lookup_rows(hidden, "LaunchVehicle")
    assert tq.lookup_rows(hidden, "LaunchVehicle", private=True)["total"] > 0


# --- aggregate ------------------------------------------------------------------------------


def test_a_named_metric_is_recomputed_with_its_id(lake):
    out = tq.aggregate(lake, metric="atlas_v_launches")
    assert out["figure"] == 5 and out["id"] == f"m:atlas_v_launches/{out['snapshot']}" and out["type"] == "Mission"


def test_a_named_sum_and_average_are_recomputed(lake):
    assert tq.aggregate(lake, metric="cheap_cost")["figure"] == tq.aggregate(
        lake, type_name="Mission", op="sum", attribute="sampleCostMillionUsd",
        filters=[{"attribute": "sample_cost_million_usd", "op": "lt", "value": "200"}])["figure"]
    assert tq.aggregate(lake, metric="mars_avg_cost")["figure"] == tq.aggregate(
        lake, type_name="Mission", op="avg", attribute="sampleCostMillionUsd",
        filters=[{"attribute": "target", "value": "Mars"}])["figure"]


def test_a_named_metric_with_not_equal(lake):
    assert tq.aggregate(lake, metric="not_atlas")["figure"] == 13


def test_a_metric_that_cannot_be_recomputed_is_refused(lake):
    assert "not recomputable" in tq.aggregate(lake, metric="ored")["error"]
    assert "not recomputable" in tq.aggregate(lake, metric="names")["error"]
    assert "does not read" in tq.aggregate(lake, metric="elsewhere")["error"]


def test_an_unknown_metric_points_to_describe(lake):
    assert "describe_structured" in tq.aggregate(lake, metric="nope")["error"]


def test_a_metric_on_the_wrong_snapshot_is_refused(lake):
    assert "is not the active snapshot" in tq.aggregate(lake, metric="atlas_v_launches", snapshot="old")["error"]


def test_a_metric_on_its_own_snapshot_is_recomputed(lake):
    snap = tq.aggregate(lake, metric="atlas_v_launches")["snapshot"]
    assert tq.aggregate(lake, metric="atlas_v_launches", snapshot=snap)["figure"] == 5


def test_an_ad_hoc_count_sum_min_and_max(lake):
    base = {"type_name": "Mission", "attribute": "sampleCostMillionUsd"}
    count = tq.aggregate(lake, type_name="Mission", op="count")
    assert count["figure"] == 18 and count["rows"] == 18 and count["id"].startswith("m:count:")
    lo, hi = tq.aggregate(lake, op="min", **base)["figure"], tq.aggregate(lake, op="max", **base)["figure"]
    assert int(lo) <= int(hi)


def test_an_ad_hoc_figure_groups_by_one_column(lake):
    out = tq.aggregate(lake, type_name="Mission", op="count", group_by="vehicle_family")
    groups = {g["group"]: g["figure"] for g in out["groups"]}
    assert groups["Atlas V"] == 5 and groups["Ariane 5"] == 3 and sum(groups.values()) == 18


def test_a_grouped_sum_reduces_each_group(lake):
    out = tq.aggregate(lake, type_name="Mission", op="sum", attribute="sampleCostMillionUsd", group_by="target")
    assert all("figure" in g for g in out["groups"]) and out["group_by"] == "target"


@pytest.mark.parametrize("kwargs,error", [
    ({"type_name": "Comet", "op": "count"}, "no mapped type"),
    ({"type_name": "Mission", "op": "median"}, "op must be one of"),
    ({"type_name": "Mission", "op": "sum"}, "needs an attribute"),
    ({"type_name": "Mission", "op": "count", "group_by": "colour"}, "no column"),
    ({"type_name": "Mission", "op": "sum", "attribute": "colour"}, "no attribute"),
    ({"type_name": "Mission", "op": "sum", "attribute": "target"}, "needs a number"),
    ({"type_name": "Mission", "op": "count", "snapshot": "old"}, "is not the active snapshot"),
])
def test_an_ad_hoc_figure_it_cannot_compute_is_an_error(lake, kwargs, error):
    assert error in tq.aggregate(lake, **kwargs)["error"]


def test_aggregate_without_a_mapping_is_an_error(tmp_path):
    assert tq.aggregate(LocalStore(tmp_path), metric="x") == {"error": "this collection has no mapped tables"}


def test_a_private_tables_figures_are_hidden_from_a_public_caller(hidden):
    assert "error" in tq.aggregate(hidden, type_name="LaunchVehicle", op="count")
    assert tq.aggregate(hidden, type_name="LaunchVehicle", op="count", private=True)["figure"] > 0
