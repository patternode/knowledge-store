"""Extraction slice: silver documents to gold at the active ontology version, over a local lake and
the deterministic fake model. Covers full extraction, rejection and retry, descriptive and
additive versions, delta selection and mapped tables."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from extraction_spec import TTL
from fake_llm import FakeClient
from knowledge_store.extraction.slices import extract
from knowledge_store.extraction.slices.extractor import Extractor, run_record
from knowledge_store.ingestion.slices.ingest import ingest
from knowledge_store.ingestion.slices.refine import refine_all, load_doc
from knowledge_store.ontology.domain import model
from knowledge_store.ontology.slices import versions
from knowledge_store.platform_services import SourceConfig, layout
from knowledge_store.platform_services.adapters.store import LocalStore
from knowledge_store.platform_services.slices.config import Profile
from test_ingest import FakeSource

PROFILE = Profile(name="Missions", description="Space missions.")

DOCS = {
    "alpha.md": "# Alpha\n\nMission Alpha was launched by Agency Nova in 2011.\n\nMission Alpha studies Planet Kiro.",
    "beta.md": "# Beta\n\nMission Beta was launched by Agency Orbis in 2014.\n\nMission Beta carries Instrument Lux.",
    "gamma.md": "# Gamma\n\nMission Gamma was launched by Agency Nova in 2019 and its instrument bay was empty.",
}

ADDITIVE = TTL.replace('owl:versionInfo "0.1.0"', 'owl:versionInfo "0.2.0"') + """
o:Instrument a owl:Class ; rdfs:label "Instrument" .
o:carries a owl:ObjectProperty ; rdfs:domain o:Mission ; rdfs:range o:Instrument .
"""

DESCRIPTIVE = TTL.replace('owl:versionInfo "0.1.0"', 'owl:versionInfo "0.1.1"').replace(
    'rdfs:label "Target body"', 'rdfs:label "Target world"')


def _dir(tmp: Path, name: str, ttl: str, mapping: str | None = None) -> Path:
    d = tmp / name
    d.mkdir()
    (d / "ontology.ttl").write_text(ttl)
    if mapping:
        (d / "mappings.yaml").write_text(mapping)
    return d


@pytest.fixture
def lake(tmp_path):
    lake = LocalStore(tmp_path / "lake")
    ingest(lake, SourceConfig("docs", "fake"), FakeSource({k: ("1", v.encode()) for k, v in DOCS.items()}))
    refine_all(lake)
    return lake


def _ids(lake) -> dict[str, str]:
    from knowledge_store.ingestion.slices.refine import silver_doc_ids
    return {load_doc(lake, d)["title"]: d for d in silver_doc_ids(lake)}


def _publish(lake, tmp_path, name="v010", ttl=TTL, mapping=None):
    return versions.publish(lake, _dir(tmp_path, name, ttl, mapping), by="test", activate=True)


def test_nothing_is_extracted_without_an_active_ontology(lake):
    assert extract.extract_all(lake, FakeClient(), "fake", PROFILE) == []


def test_every_document_is_extracted_once_at_the_active_version(lake, tmp_path):
    _publish(lake, tmp_path)
    rows = extract.extract_all(lake, FakeClient(), "fake", PROFILE, workers=2, run_id="run-1")
    assert {r["status"] for r in rows} == {"extracted"} and len(rows) == 3
    for r in rows:
        assert lake.exists(layout.graph_key("0.1.0", r["doc_id"]))
        assert r["run"]["run_id"] == "run-1" and "result" not in r
        held = json.loads(lake.get(layout.extraction_key("0.1.0", r["doc_id"])))
        assert held["counts"]["entities"] >= 2 and held["delta"] is False
    assert extract.extract_all(lake, FakeClient(), "fake", PROFILE) == []


def test_a_document_with_an_unknown_thing_writes_its_candidates(lake, tmp_path):
    _publish(lake, tmp_path)
    extract.extract_all(lake, FakeClient(), "fake", PROFILE)
    beta = _ids(lake)["Beta"]
    lines = lake.get(layout.candidates_key("0.1.0", beta)).decode().splitlines()
    assert [json.loads(x)["term"] for x in lines] == ["Instrument"]


class Failing:
    def converse(self, **kw):
        raise PermissionError("no model access")


def test_a_failed_document_is_rejected_and_retried_only_when_asked(lake, tmp_path):
    _publish(lake, tmp_path)
    rows = extract.extract_all(lake, Failing(), "fake", PROFILE)
    assert {r["status"] for r in rows} == {"rejected"} and "no model access" in rows[0]["error"]
    assert lake.exists(layout.rejected_key("0.1.0", rows[0]["doc_id"]))
    assert extract.extract_all(lake, FakeClient(), "fake", PROFILE) == []
    again = extract.extract_all(lake, FakeClient(), "fake", PROFILE, retry_rejected=True)
    assert {r["status"] for r in again} == {"extracted"}


def test_the_limit_caps_the_documents_extracted(lake, tmp_path):
    _publish(lake, tmp_path)
    assert len(extract.extract_all(lake, FakeClient(), "fake", PROFILE, limit=1)) == 1


def test_a_descriptive_version_extracts_nothing_new(lake, tmp_path):
    _publish(lake, tmp_path)
    extract.extract_all(lake, FakeClient(), "fake", PROFILE)
    m = _publish(lake, tmp_path, "v011", DESCRIPTIVE)
    assert m["kind"] == "descriptive"
    rows = extract.extract_all(lake, FakeClient(), "fake", PROFILE)
    assert {r["status"] for r in rows} == {"not_selected"}
    assert all("descriptive version" in r["reason"] for r in rows)


def test_an_additive_version_extracts_only_documents_that_show_the_new_terms(lake, tmp_path):
    _publish(lake, tmp_path)
    extract.extract_all(lake, FakeClient(), "fake", PROFILE)
    m = _publish(lake, tmp_path, "v020", ADDITIVE)
    assert m["kind"] == "additive" and set(m["delta_terms"]) == {"Instrument", "carries"}
    rows = {load_doc(lake, r["doc_id"])["title"]: r for r in extract.extract_all(lake, FakeClient(), "fake", PROFILE)}
    assert rows["Alpha"]["status"] == "not_selected" and rows["Alpha"]["reason"] == "no sign of the new terms"
    assert rows["Beta"]["status"] == "extracted" and rows["Beta"]["run"]["selected"] == "candidate"
    assert rows["Gamma"]["status"] == "extracted" and rows["Gamma"]["run"]["selected"] == "lexical"
    beta = json.loads(lake.get(layout.extraction_key("0.2.0", _ids(lake)["Beta"])))
    assert beta["delta"] is True
    assert [e["type"] for e in beta["result"]["entities"]] == ["Instrument"]


def test_all_delta_selects_every_held_document(lake, tmp_path):
    _publish(lake, tmp_path)
    extract.extract_all(lake, FakeClient(), "fake", PROFILE)
    _publish(lake, tmp_path, "v020", ADDITIVE)
    rows = extract.extract_all(lake, FakeClient(), "fake", PROFILE, all_delta=True)
    assert {r["run"]["selected"] for r in rows} == {"all"}


def test_a_new_subclass_selects_documents_holding_its_parent_for_retyping(lake, tmp_path):
    _publish(lake, tmp_path)
    extract.extract_all(lake, FakeClient(), "fake", PROFILE)
    sub = TTL.replace('owl:versionInfo "0.1.0"', 'owl:versionInfo "0.2.0"') + \
        'o:Lander a owl:Class ; rdfs:subClassOf o:Mission ; rdfs:label "Lander" .\n'
    _publish(lake, tmp_path, "v020", sub)
    spec, _ = versions.load_version(lake, "0.2.0")
    alpha = _ids(lake)["Alpha"]
    assert extract.select_for_delta(lake, spec, ["Lander"], ["0.2.0", "0.1.0"], alpha, ["0.1.0"]) == "retype"


def test_held_at_names_the_versions_with_a_graph(lake, tmp_path):
    _publish(lake, tmp_path)
    extract.extract_all(lake, FakeClient(), "fake", PROFILE)
    alpha = _ids(lake)["Alpha"]
    assert extract.held_at(lake, ["0.2.0", "0.1.0"], alpha) == ["0.1.0"]


def test_known_entities_are_numbered_with_their_most_specific_type(lake, tmp_path):
    _publish(lake, tmp_path)
    extract.extract_all(lake, FakeClient(), "fake", PROFILE)
    spec = model.load(data=TTL)
    known = extract.known_entities(lake, spec, ["0.1.0"], _ids(lake)["Alpha"])
    assert sorted(known) == ["k1", "k2", "k3"]
    assert {(v["type"], v["name"]) for v in known.values()} == {
        ("Mission", "Mission Alpha"), ("SpaceAgency", "Agency Nova"), ("TargetBody", "Planet Kiro")}


def test_extract_one_writes_the_graph_and_returns_the_row_without_the_result(lake, tmp_path):
    _publish(lake, tmp_path)
    spec, shapes = versions.load_version(lake, "0.1.0")
    alpha = _ids(lake)["Alpha"]
    row = extract.extract_one(lake, Extractor(FakeClient(), "fake", spec, PROFILE, shapes=shapes), "0.1.0", alpha,
                              run_record("r", "fake", "0.1.0"))
    assert row["status"] == "extracted" and "result" not in row and row["candidates"] == 0
    assert not lake.exists(layout.candidates_key("0.1.0", alpha))


MAPPED_TTL = TTL + 'o:agencyCode a owl:DatatypeProperty ; rdfs:domain o:SpaceAgency .\n'
MAPPING = """
tables:
  agencies:
    location: tables/agencies.csv
    logical_table: agencies
    class: SpaceAgency
    key: [code]
    columns:
      code: {attribute: agencyCode}
"""


def test_a_file_a_mapping_names_is_a_table_and_is_not_extracted(tmp_path):
    lake = LocalStore(tmp_path / "lake")
    ingest(lake, SourceConfig("docs", "fake"), FakeSource({
        "alpha.md": ("1", DOCS["alpha.md"].encode()),
        "tables/agencies.csv": ("1", b"code\nNOVA\nORBIS\n" + b"# padding row to pass the refine minimum\n")}))
    refine_all(lake)  # before the mapping exists, the table is refined like any document
    _publish(lake, tmp_path, ttl=MAPPED_TTL, mapping=MAPPING)
    rows = extract.extract_all(lake, FakeClient(), "fake", PROFILE)
    assert [load_doc(lake, r["doc_id"])["title"] for r in rows] == ["Alpha"]
