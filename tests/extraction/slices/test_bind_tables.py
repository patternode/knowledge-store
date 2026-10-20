"""Extraction slice: binding mapped tables into gold, over a local lake. The catalogue-wide
behaviour (queries, citations) is in test_structured_fixes.py; this file covers the binding
itself: choosing the file, reading rows, cells, joins, misses and rebinding."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from extraction_spec import TTL
from knowledge_store.extraction.slices import bind_tables as bt
from knowledge_store.ingestion.slices.ingest import ingest
from knowledge_store.ontology.domain.mapping import Column, Mapping, Table
from knowledge_store.ontology.slices import versions
from knowledge_store.platform_services import SourceConfig, layout
from knowledge_store.platform_services.adapters.store import LocalStore
from test_ingest import FakeSource

ONTO = TTL + """
o:name a owl:DatatypeProperty .
o:agencyCode a owl:DatatypeProperty ; rdfs:domain o:SpaceAgency .
"""

MAPPING = """
tables:
  missions:
    location: tables/missions.csv
    logical_table: missions
    class: Mission
    key: [mission_id]
    columns:
      name: {attribute: name}
      launch_year: {attribute: launchYear, datatype: xsd:integer}
      agency: {relation: launchedBy, range: SpaceAgency, match: agencyCode}
  agencies:
    location: tables/agencies.csv
    logical_table: agencies
    class: SpaceAgency
    key: [code]
    columns:
      code: {attribute: agencyCode}
"""

MISSIONS = b"mission_id,name,launch_year,agency\nm1,Alpha,2011,NOVA\nm2,Beta,soon,ORBIS\nm3,Gamma,2019,ZED\n,NoKey,2020,NOVA\nm1,Dup,2011,NOVA\n"
AGENCIES = b"code\nNOVA\nORBIS\n"


def _publish(lake, tmp: Path, ttl=ONTO, mapping=MAPPING, name="v010"):
    d = tmp / name
    d.mkdir()
    (d / "ontology.ttl").write_text(ttl)
    (d / "mappings.yaml").write_text(mapping)
    return versions.publish(lake, d, by="test", activate=True)


def _upload(lake, files: dict[str, bytes], source="tables", scope="public"):
    ingest(lake, SourceConfig(source, "fake", scope=scope), FakeSource({k: ("1", v) for k, v in files.items()}))


@pytest.fixture
def lake(tmp_path):
    return LocalStore(tmp_path / "lake")


def _cells(lake, row):
    return [json.loads(x) for x in lake.get(row["cells"]).decode().splitlines()]


# --- the version and its mapping ---------------------------------------------------------------

def test_without_an_active_version_there_is_no_mapping_or_binding(lake):
    assert bt.active(lake) is None
    assert bt.published_mapping(lake) is None
    assert bt.binding(lake) == {}
    assert bt.mapped_doc_ids(lake) == set()
    assert bt.bind(lake) == {"written": 0, "unchanged": 0, "missing": [], "misses": []}


def test_a_version_without_a_mapping_binds_nothing(lake, tmp_path):
    d = tmp_path / "plain"
    d.mkdir()
    (d / "ontology.ttl").write_text(TTL)
    versions.publish(lake, d, by="test", activate=True)
    assert bt.active(lake) == "0.1.0" and bt.published_mapping(lake) is None
    assert bt.bind(lake)["written"] == 0


def test_the_chain_stops_at_a_full_version(lake, tmp_path):
    _publish(lake, tmp_path)
    _publish(lake, tmp_path, ONTO.replace('"0.1.0"', '"0.2.0"') + 'o:Lander a owl:Class .\n', name="v020")
    assert bt.chain(lake, "0.2.0") == ["0.2.0", "0.1.0"]
    assert bt.chain(lake, "9.9.9") == ["9.9.9"]


# --- choosing the file -------------------------------------------------------------------------

def test_a_path_matches_exactly_by_suffix_or_by_name_in_that_order():
    meta = {"source_key": "landing/tables/missions.csv"}
    assert bt._rank({"source_key": "tables/missions.csv"}, "tables/missions.csv") == 0
    assert bt._rank(meta, "tables/missions.csv") == 1
    assert bt._rank({"source_key": "other/missions.csv"}, "tables/missions.csv") == 2
    assert bt._rank(meta, "tables/agencies.csv") == -1
    assert bt._rank(meta, "") == -1
    assert bt.matches(meta, "/tables/missions.csv")


def test_every_upload_name_and_the_adapters_folder_count_as_paths():
    meta = {"source_key": "a\\x.csv", "source_keys": ["a\\x.csv", "b/y.csv"], "name": "z.csv",
            "metadata": {"folder": "/f/"}}
    assert bt._paths(meta) == ["a/x.csv", "b/y.csv", "f/z.csv"]
    assert bt._paths({"name": "only.csv"}) == ["only.csv"]


def test_two_equally_good_files_are_not_a_guess():
    objs = {"d1": {"source_key": "a/missions.csv"}, "d2": {"source_key": "b/missions.csv"}}
    assert bt._select(objs, "tables/missions.csv") == (None, "more than one file named missions.csv")
    assert bt._select(objs, "a/missions.csv")[0][0] == "d1"
    assert bt._select(objs, "nothing.csv") == (None, "")


def test_mapped_files_are_known_before_refine(lake, tmp_path):
    _upload(lake, {"tables/missions.csv": MISSIONS, "tables/agencies.csv": AGENCIES, "notes.md": b"# notes"})
    _publish(lake, tmp_path)
    assert bt.mapped_doc_ids(lake) == {layout.sha256(MISSIONS), layout.sha256(AGENCIES)}


# --- reading rows ------------------------------------------------------------------------------

def test_csv_rows_are_trimmed_and_blank_rows_and_headers_dropped():
    rows = bt._read_rows(b"\xef\xbb\xbfa, b,\n 1 ,2,x\n,,\n", "t.csv")
    assert rows == [{"a": "1", "b": "2"}]


def test_tsv_is_read_with_tabs():
    assert bt._read_rows(b"a\tb\n1\t2\n", "t.tsv") == [{"a": "1", "b": "2"}]


def test_json_rows_are_objects_with_nulls_as_empty():
    assert bt._read_rows(b'[{"a": 1, "b": null}]', "t.json") == [{"a": "1", "b": ""}]


@pytest.mark.parametrize("data,location,reason", [
    (b"\xff\xfe", "t.csv", "not UTF-8"),
    (b"{", "t.json", "not valid JSON"),
    (b'{"a": 1}', "t.json", "not a JSON array of objects"),
    (b"[1]", "t.json", "not a JSON array of objects"),
    (b"a,a\n1,2\n", "t.csv", "more than one column named a"),
])
def test_an_unreadable_file_says_why(data, location, reason):
    with pytest.raises(ValueError, match=reason):
        bt._read_rows(data, location)


def test_a_file_over_the_size_or_row_limit_is_refused(monkeypatch):
    monkeypatch.setattr(bt, "MAX_TABLE_BYTES", 5)
    with pytest.raises(ValueError, match="larger than"):
        bt._read_rows(b"a\n1\n2\n", "t.csv")
    monkeypatch.setattr(bt, "MAX_TABLE_BYTES", 100)
    monkeypatch.setattr(bt, "MAX_TABLE_ROWS", 1)
    with pytest.raises(ValueError, match="more than 1 rows"):
        bt._read_rows(b"a\n1\n2\n", "t.csv")


# --- keys --------------------------------------------------------------------------------------

def test_one_key_column_is_its_value():
    assert bt.key_text(["a,b"]) == "a,b"


def test_several_key_columns_escape_commas_and_percent_signs_and_round_trip():
    table = Table("t", "t.csv", "t", "Mission", ("a", "b"), ())
    text = bt.key_text(["x,1", "50%"])
    assert text == "x%2C1,50%25"
    assert bt.key_parts(table, text) == ["x,1", "50%"]
    assert bt.key_parts(Table("t", "t.csv", "t", "Mission", ("a",), ()), "x,1") == ["x,1"]


def test_a_mapping_change_changes_its_hash():
    a = Table("t", "t.csv", "t", "Mission", ("a",), (Column("n", attribute="name"),))
    same = Table("t", "t.csv", "t", "Mission", ("a",), (Column("n", attribute="name", datatype="string"),))
    other = Table("t", "t.csv", "t", "Mission", ("a",), (Column("n", attribute="name", datatype="integer"),))
    assert bt.mapping_hash(a) == bt.mapping_hash(same) != bt.mapping_hash(other)


def test_a_private_table_or_file_is_private():
    t = Table("t", "t.csv", "t", "Mission", ("a",), ())
    assert bt._scope(t, {}) == "public"
    assert bt._scope(t, {"scope": "private"}) == "private"
    assert bt._scope(Table("t", "t.csv", "t", "Mission", ("a",), (), scope="private"), {}) == "private"


# --- binding -----------------------------------------------------------------------------------

def test_mapped_tables_are_bound_with_cells_joins_and_misses(lake, tmp_path):
    _upload(lake, {"tables/missions.csv": MISSIONS, "tables/agencies.csv": AGENCIES})
    _publish(lake, tmp_path)
    report = bt.bind(lake)
    assert report["written"] == 2 and report["unchanged"] == 0 and report["tables"] == ["agencies", "missions"]
    reasons = [m["reason"] for m in report["misses"]]
    assert "row has no key" in reasons
    assert any(r.startswith("no SpaceAgency with agencyCode 'ZED'") for r in reasons)
    assert sum("soon" in r or "integer" in r.lower() for r in reasons) == 1
    b = bt.binding(lake)
    assert b["missions"]["rows"] == 3 and b["missions"]["class"] == "Mission"  # m1's duplicate row is dropped
    cells = _cells(lake, b["missions"])
    year = next(c for c in cells if c["key"] == "m2" and c["column"] == "launch_year")
    assert year["invalid"] is True and year["value"] == "soon"
    key_cell = next(c for c in cells if c["key"] == "m1" and c["column"] == "mission_id")
    assert key_cell["datatype"] == "string"
    graph = lake.get(b["missions"]["graph"]).decode()
    assert "launchedBy" in graph and "NOVA" in graph


def test_an_unchanged_table_is_not_rebound(lake, tmp_path):
    _upload(lake, {"tables/missions.csv": MISSIONS, "tables/agencies.csv": AGENCIES})
    _publish(lake, tmp_path)
    bt.bind(lake)
    again = bt.bind(lake)
    assert again["written"] == 0 and again["unchanged"] == 2


def test_a_missing_file_a_live_source_and_an_unreadable_file_are_reported(lake, tmp_path):
    mapping = MAPPING.replace("tables/agencies.csv", "coa:agency-source")
    _upload(lake, {"tables/missions.csv": b"a,a\n1,2\n"})
    _publish(lake, tmp_path, mapping=mapping)
    report = bt.bind(lake)
    assert {"table": "agencies", "reason": "live source, not copied"} in report["missing"]
    unreadable = next(m for m in report["missing"] if m["table"] == "missions")
    assert "more than one column" in unreadable["reason"]

    lake2 = LocalStore(tmp_path / "lake2")
    _publish(lake2, tmp_path, name="other")
    report = bt.bind(lake2)
    assert {"table": "missions", "location": "tables/missions.csv"} in report["missing"]


def test_an_ambiguous_file_is_reported_with_the_reason(lake, tmp_path):
    _upload(lake, {"a/agencies.csv": AGENCIES, "b/agencies.csv": AGENCIES + b"EXTRA\n",
                   "tables/missions.csv": MISSIONS})
    _publish(lake, tmp_path)
    missing = {m["table"]: m for m in bt.bind(lake)["missing"]}
    assert missing["agencies"]["reason"] == "more than one file named agencies.csv"


def test_a_value_shared_by_two_rows_is_not_joined(lake, tmp_path):
    onto = ONTO + 'o:region a owl:DatatypeProperty ; rdfs:domain o:SpaceAgency .\n'
    mapping = MAPPING.replace("match: agencyCode", "match: region").replace(
        "      code: {attribute: agencyCode}", "      code: {attribute: agencyCode}\n      region: {attribute: region}")
    _upload(lake, {"tables/missions.csv": b"mission_id,name,launch_year,agency\nm1,A,2011,EU\n",
                   "tables/agencies.csv": b"code,region\nNOVA,EU\nORBIS,EU\n"})
    _publish(lake, tmp_path, ttl=onto, mapping=mapping)
    misses = bt.bind(lake)["misses"]
    assert any(m.get("column") == "agency" and "'EU'" in m["reason"] for m in misses)


def test_a_snapshot_that_fails_its_shapes_is_not_written(lake, tmp_path):
    shapes = """@prefix sh: <http://www.w3.org/ns/shacl#> . @prefix o: <https://example.org/missions#> .
    o:NeedsCode a sh:NodeShape ; sh:targetClass o:SpaceAgency ;
        sh:property [ sh:path o:agencyCode ; sh:minLength 10 ; sh:message "codes are long" ] .
    """
    d = tmp_path / "shaped"
    d.mkdir()
    (d / "ontology.ttl").write_text(ONTO)
    (d / "shapes.ttl").write_text(shapes)
    (d / "mappings.yaml").write_text(MAPPING)
    versions.publish(lake, d, by="test", activate=True)
    _upload(lake, {"tables/missions.csv": MISSIONS, "tables/agencies.csv": AGENCIES})
    report = bt.bind(lake)
    failed = next(m for m in report["misses"] if m["table"] == "agencies")
    assert failed["reason"] == "snapshot failed SHACL" and failed["messages"]
    assert "agencies" not in bt.binding(lake)


def test_a_table_the_mapping_drops_leaves_the_binding(lake, tmp_path):
    _upload(lake, {"tables/missions.csv": MISSIONS, "tables/agencies.csv": AGENCIES})
    _publish(lake, tmp_path)
    bt.bind(lake)
    only_agencies = """
tables:
  agencies:
    location: tables/agencies.csv
    logical_table: agencies
    class: SpaceAgency
    key: [code]
    columns:
      code: {attribute: agencyCode}
"""
    _publish(lake, tmp_path, ttl=ONTO.replace('"0.1.0"', '"1.0.0"'), mapping=only_agencies, name="v100")
    assert bt.bind(lake)["tables"] == ["agencies"]


def test_a_binding_falls_back_along_the_chain(lake):
    lake.put(layout.ONTOLOGY_ACTIVE, json.dumps({"version": "0.2.0"}).encode())
    lake.put(f"{layout.ontology_version_prefix('0.2.0')}/manifest.json", json.dumps({"kind": "additive", "base": "0.1.0"}).encode())
    lake.put(layout.structured_binding_key("0.1.0"), json.dumps({"t": {"snapshot": "old"}}).encode())
    lake.put(layout.structured_binding_key("0.2.0"), json.dumps({"u": {"snapshot": "new"}}).encode())
    assert bt.binding(lake) == {"u": {"snapshot": "new"}, "t": {"snapshot": "old"}}
    assert Mapping().locations() == set()
