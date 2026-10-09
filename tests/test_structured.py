"""Mapped tables: publish checks the mapping, bind copies the CSVs, and the tools read cells.

The space-missions catalog is the fixture. A directory with no mapping still publishes as before;
that path is the lifecycle test.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from knowledge_store import collections, layout
from knowledge_store.config import SourceConfig
from knowledge_store.ontology import renditions, versions
from knowledge_store.pipeline import project, refine
from knowledge_store.pipeline.ingest import ingest_source
from knowledge_store.store import LocalStore, put_json
from knowledge_store.structured.bind import bind, binding, mapped_doc_ids
from knowledge_store.structured.mapping import Mapping, Table, load as load_mapping, r2rml
from knowledge_store.structured.query import aggregate, lookup_rows, values_equal
from knowledge_store.tools import gateway

ROOT = Path(__file__).resolve().parents[1]
ONTO = ROOT / "examples/space-missions/ontology"
CORPUS = ROOT / "examples/space-missions"


def _copy(tmp: Path, version: str | None = None) -> Path:
    dest = tmp / "onto"
    shutil.copytree(ONTO, dest)
    if version:
        ttl = (dest / "ontology.ttl").read_text()
        ttl = ttl.replace('owl:versionInfo "1.0.0"', f'owl:versionInfo "{version}"')
        ttl = ttl.replace("https://example.org/missions/1.0.0", f"https://example.org/missions/{version}")
        (dest / "ontology.ttl").write_text(ttl)
    return dest


def _edit(path: Path, old: str, new: str) -> None:
    path.write_text(path.read_text().replace(old, new, 1))


def _set_version(dest: Path, version: str) -> None:
    import re
    ttl = (dest / "ontology.ttl").read_text()
    ttl = re.sub(r'owl:versionInfo "[^"]+"', f'owl:versionInfo "{version}"', ttl, count=1)
    ttl = re.sub(r"<https://example.org/missions/\d+\.\d+\.\d+>",
                 f"<https://example.org/missions/{version}>", ttl, count=1)
    (dest / "ontology.ttl").write_text(ttl)


_NEW_METRIC = """
  - name: mission_rows
    description: How many rows the missions table holds.
    expression:
      dialects:
        - dialect: ANSI_SQL
          expression: "SELECT COUNT(*) FROM missions"
    custom_extensions:
      - vendor_name: COA
        data:
          source_table: missions
          ontology_concepts: [Mission]
"""


def _corpus(tmp: Path) -> Path:
    dest = tmp / "corpus"
    shutil.copytree(CORPUS / "tables", dest / "tables")
    (dest / "tables" / "notes.csv").write_text(
        "title,body\n"
        "memo,\"This catalog note is long enough to become a passage about the collection itself.\"\n")
    return dest


def _collection(tmp: Path):
    root = LocalStore(tmp / "root")
    put_json(root, collections.CONFIG, [{"id": "missions"}])
    return root, collections.scoped(root, "missions")


def test_publish_checks_the_mapping_and_writes_the_same_rendition_twice(tmp_path):
    spec, ttl, shapes = renditions.read_master(ONTO)
    mapping = load_mapping(ONTO, spec)
    assert mapping is not None and {t.logical_table for t in mapping.tables} == {"missions", "launch_vehicles"}
    one, two = renditions.render_all(spec, ttl, shapes, mapping), renditions.render_all(spec, ttl, shapes, mapping)
    assert one == two
    assert one["r2rml/mapping.ttl"].decode() == r2rml(spec, mapping)
    assert (ONTO / "r2rml-mapping.ttl").read_text() == r2rml(spec, mapping)
    bare = renditions.render_all(spec, ttl, shapes, None)
    assert "structured/mapping.json" not in bare and "r2rml/mapping.ttl" not in bare

    lake = LocalStore(tmp_path / "lake")
    manifest = versions.publish(lake, ONTO, by="test", activate=True)
    assert manifest["kind"] == "initial"
    assert "mappings.yaml" in manifest["sha256"] and "metrics.osi.yaml" in manifest["sha256"]
    pre = layout.ontology_version_prefix("1.0.0")
    assert lake.get(f"{pre}/renditions/r2rml/mapping.ttl") == one["r2rml/mapping.ttl"]
    assert "Mapped tables" in lake.get(f"{pre}/renditions/agent/ontology.md").decode()


def test_a_class_the_ontology_lacks_is_refused(tmp_path):
    dest = _copy(tmp_path)
    _edit(dest / "mappings.yaml", "class: Mission", "class: NotAClass")
    with pytest.raises(ValueError, match="NotAClass"):
        versions.publish(LocalStore(tmp_path / "lake"), dest)


def test_an_identical_ontology_and_mapping_is_refused(tmp_path):
    lake = LocalStore(tmp_path / "lake")
    versions.publish(lake, _copy(tmp_path / "a"), activate=True)
    with pytest.raises(ValueError, match="identical"):
        versions.publish(lake, _copy(tmp_path / "b", "1.0.1"))


def test_mapping_bumps_follow_the_change(tmp_path):
    lake = LocalStore(tmp_path / "lake")
    versions.publish(lake, _copy(tmp_path / "base"), activate=True)

    wording = _copy(tmp_path / "wording", "1.0.1")
    _edit(wording / "metrics.osi.yaml",
          "How many catalogued missions launched on a vehicle in the Atlas V family.",
          "How many catalogued missions launched on a vehicle in the Atlas V family. Wording only.")
    patch = versions.publish(lake, wording, activate=True)
    assert patch["kind"] == "descriptive" and patch["delta_terms"] == []

    added = tmp_path / "added"
    shutil.copytree(wording, added)
    _set_version(added, "1.0.2")
    (added / "metrics.osi.yaml").write_text((added / "metrics.osi.yaml").read_text() + _NEW_METRIC)
    with pytest.raises(ValueError, match="needs a minor bump"):
        versions.publish(lake, added)
    minor = tmp_path / "minor"
    shutil.copytree(added, minor)
    _set_version(minor, "1.1.0")
    published = versions.publish(lake, minor, activate=True)
    assert published["kind"] == "additive" and published["delta_terms"] == []

    semantic = tmp_path / "semantic"
    shutil.copytree(minor, semantic)
    _set_version(semantic, "1.2.0")
    _edit(semantic / "mappings.yaml", "key: [mission_id]", "key: [name]")
    with pytest.raises(ValueError, match="needs a major bump"):
        versions.publish(lake, semantic)
    major = tmp_path / "major"
    shutil.copytree(semantic, major)
    _set_version(major, "2.0.0")
    assert versions.publish(lake, major, activate=True)["kind"] == "semantic"


def test_a_live_location_is_not_a_file_and_is_not_copied(tmp_path):
    assert Mapping(tables=(Table("missions", "coa:ds1", "missions", "Mission", ("mission_id",), ()),)).locations() == set()
    dest = _copy(tmp_path)
    _edit(dest / "mappings.yaml", "location: tables/missions.csv", "location: coa:ds1")
    lake = LocalStore(tmp_path / "lake")
    versions.publish(lake, dest, activate=True)
    report = bind(lake)
    assert {"table": "missions", "reason": "live source, not copied"} in report["missing"]
    assert "missions" not in binding(lake)


def test_the_catalog_is_bound_skipped_and_queried(tmp_path):
    root, lake = _collection(tmp_path)
    versions.publish(lake, ONTO, by="test", activate=True)
    corpus = _corpus(tmp_path)
    ingest_source(lake, SourceConfig("missions-tables", "local_dir", {"path": str(corpus), "pattern": "**/*.csv"}))
    refined = refine.refine_all(lake)
    assert {r["status"] for r in refined} == {"mapped", "refined"}
    mapped = mapped_doc_ids(lake)
    assert len(mapped) == 2
    for doc_id in mapped:
        assert not lake.exists(layout.doc_key(doc_id))
        assert json.loads(lake.get(layout.skipped_key(doc_id)))["status"] == "mapped"
    assert refine.silver_doc_ids(lake)  # the unmapped notes.csv
    assert refine.refine_all(lake) == []

    report = bind(lake)
    assert report["written"] == 2 and report["misses"] == [], report["misses"]
    assert bind(lake)["unchanged"] == 2 and bind(lake)["written"] == 0

    juno = lookup_rows(lake, "Mission", [{"attribute": "name", "op": "eq", "value": "Juno"}])
    assert juno["total"] == 1
    cost = juno["rows"][0]["values"]["sampleCostMillionUsd"]
    assert cost["value"] == "1100"
    assert cost["cell"] == f"c:missions-tables/{juno['snapshot']}/missions/juno/sample_cost_million_usd"
    vehicle = juno["rows"][0]["values"]["launchedOn"]
    assert vehicle["value"] == "atlas-v-551"
    named = lookup_rows(lake, "LaunchVehicle", [{"attribute": "vehicleId", "op": "eq", "value": "atlas-v-551"}])
    assert named["rows"][0]["values"]["name"]["value"] == "Atlas V 551"

    figure = aggregate(lake, metric="atlas_v_launches")
    assert figure["figure"] == 5
    assert figure["id"] == f"m:atlas_v_launches/{figure['snapshot']}"
    adhoc = aggregate(lake, type_name="Mission", op="count",
                      filters=[{"attribute": "vehicleFamily", "op": "eq", "value": "Atlas V"}])
    assert adhoc["figure"] == 5
    total = aggregate(lake, type_name="Mission", op="sum", attribute="sampleCostMillionUsd",
                      filters=[{"attribute": "vehicleFamily", "op": "eq", "value": "Atlas V"}])
    assert total["figure"] == 7800
    capped = lookup_rows(lake, "Mission", limit=2)
    assert capped["truncated"] and capped["total"] > 2 and len(capped["rows"]) == 2
    assert lookup_rows(lake, "Mission", [{"attribute": "name", "op": "prefix", "value": "Jun"}])["total"] == 1

    cells = lookup_rows(lake, "", cell_ids=[cost["cell"]])["cells"]
    assert cells[0]["value"] == "1100" and cells[0]["datatype"] == "integer"
    assert any(col["column"] == "name" and col["value"] == "Juno" for col in cells[0]["row"])
    assert any(col["cell"] == cost["cell"] and col["value"] == "1100" for col in cells[0]["row"])
    assert values_equal("1100", "1100", "integer") and not values_equal("999", "1100", "integer")

    via = gateway.call(root, "aggregate", {"collection": "missions", "metric": "atlas_v_launches"})
    assert via["figure"] == 5
    described = gateway.call(root, "describe_structured", {"collection": "missions"})
    assert {t["type"] for t in described["types"]} == {"Mission", "LaunchVehicle"}

    counts = project.project(lake)
    ents = json.loads(lake.get(layout.index_key("1.0.0", "entities")))
    mission = next(e for e in ents if e["label"] == "Juno")
    rocket = next(e for e in ents if e["label"] == "Atlas V 551")
    assert any(a["p"] == "sampleCostMillionUsd" and a["v"] == "1100" for a in mission["attributes"])
    assert any(r["p"] == "launchedOn" and r["o"] == rocket["id"] for r in mission["out"])
    assert mission["passages"] == [] and mission["scope"] == "public"
    assert counts["entities"] == len(ents)


def test_a_cited_figure_is_recomputed(tmp_path):
    pytest.importorskip("pydantic")
    from knowledge_store.agent import app as agent_app
    from knowledge_store.agent.grounding import Citation, Claim, GroundedAnswer, check, render
    root, lake = _collection(tmp_path)
    versions.publish(lake, ONTO, by="test", activate=True)
    ingest_source(lake, SourceConfig("missions-tables", "local_dir",
                                     {"path": str(CORPUS), "pattern": "tables/*.csv"}))
    assert bind(lake)["misses"] == []
    cost = lookup_rows(lake, "Mission", [{"attribute": "name", "op": "eq", "value": "Juno"}])["rows"][0]["values"]["sampleCostMillionUsd"]
    cell = lookup_rows(lake, "", cell_ids=[cost["cell"]])["cells"][0]
    kept, failures = check(GroundedAnswer(answerable=True, claims=[Claim(
        text="The catalog gives Juno a sample cost of 1100.",
        citations=[Citation(cell_id=cost["cell"], value="1100")])]), {}, {cost["cell"]: cell})
    assert kept and not failures
    shown = render(kept, {}, [], {cost["cell"]: cell})
    assert shown["sources"][0]["kind"] == "cell"
    assert any(col["column"] == "sample_cost_million_usd" and col["value"] == "1100" for col in shown["sources"][0]["row"])
    dropped, why = check(GroundedAnswer(answerable=True, claims=[Claim(
        text="The catalog gives Juno a sample cost of 999.",
        citations=[Citation(cell_id=cost["cell"], value="999")])]), {}, {cost["cell"]: cell})
    assert not dropped and why

    figure = aggregate(lake, metric="atlas_v_launches")

    class Tools:
        def call(self, name, args):
            return gateway.call(root, name, args)

    stated = GroundedAnswer(answerable=True, claims=[Claim(
        text="Nine catalogued missions launched on an Atlas V.",
        citations=[Citation(metric_id=figure["id"], figure="9")])])
    recomputed = agent_app._metrics(Tools(), "missions", stated)
    assert recomputed[figure["id"]]["figure"] == 5
    assert not check(stated, {}, {}, recomputed)[0]
    assert check(GroundedAnswer(answerable=True, claims=[Claim(
        text="Five catalogued missions launched on an Atlas V.",
        citations=[Citation(metric_id=figure["id"], figure="5")])]), {}, {}, recomputed)[0]


def test_a_private_table_is_hidden_and_a_broken_snapshot_is_not_activated(tmp_path):
    root, lake = _collection(tmp_path)
    dest = _copy(tmp_path)
    _edit(dest / "mappings.yaml", "class: LaunchVehicle\n    key:", "class: LaunchVehicle\n    scope: private\n    key:")
    versions.publish(lake, dest, activate=True)
    ingest_source(lake, SourceConfig("missions-tables", "local_dir",
                                     {"path": str(CORPUS), "pattern": "tables/*.csv"}))
    report = bind(lake)
    assert report["misses"] == [], report["misses"]
    public = lookup_rows(lake, "LaunchVehicle")
    private = lookup_rows(lake, "LaunchVehicle", private=True)
    assert public["total"] == 0 and private["total"] > 0
    hidden = private["rows"][0]["values"]["name"]["cell"]
    assert lookup_rows(lake, "", cell_ids=[hidden])["cells"] == []
    assert lookup_rows(lake, "", cell_ids=[hidden], private=True)["cells"]
    assert gateway.call(root, "lookup_rows", {"collection": "missions", "type": "LaunchVehicle"})["total"] == 0
    assert gateway.call(root, "lookup_rows",
                        {"collection": "missions", "type": "LaunchVehicle", "caller_private": True})["total"] > 0

    _, broken = _collection(tmp_path / "broken")
    shaped = _copy(tmp_path / "shaped")
    (shaped / "shapes.ttl").write_text(
        "@prefix sh: <http://www.w3.org/ns/shacl#> .\n"
        "@prefix o: <https://example.org/missions#> .\n"
        "o:MissionShape a sh:NodeShape ;\n"
        "    sh:targetClass o:Mission ;\n"
        "    sh:property [ sh:path o:name ; sh:minCount 1 ; sh:minLength 500 ] .\n")
    versions.publish(broken, shaped, activate=True)
    ingest_source(broken, SourceConfig("missions-tables", "local_dir",
                                       {"path": str(CORPUS), "pattern": "tables/*.csv"}))
    failed = bind(broken)
    assert "missions" not in binding(broken)
    assert any(m.get("table") == "missions" and m.get("reason") == "snapshot failed SHACL" for m in failed["misses"])
    assert "launch_vehicles" in binding(broken)
    assert lookup_rows(broken, "Mission").get("rows") == []
