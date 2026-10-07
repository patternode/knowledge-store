"""Two ways to start a collection's ontology: bring one (ontology/provided.py) or discover one,
reviewed before anyone curates it (ontology/review.py)."""

from __future__ import annotations

import pytest

from fake_llm import FakeClient
from knowledge_store import layout
from knowledge_store.ontology import provided, review, versions, writer
from knowledge_store.pipeline import run
from knowledge_store.store import get_json
from test_lifecycle import PROFILE, _collection_lake

DRAFT = {
    "classes": [{"name": "Mission", "definition": "A space mission."},
                {"name": "Organisation", "definition": "Any organisation."},
                {"name": "SpaceAgency", "definition": "An agency that flies missions."},
                {"name": "Agency", "definition": "Same as a space agency.", "synonyms": ["space office"]},
                {"name": "Planet", "definition": "A planet."},
                {"name": "Moon", "definition": "A moon.", "parent": "Planet"}],
    "relations": [{"name": "launchedBy", "definition": "Who launched it.", "domain": "Mission", "range": "Agency"},
                  {"name": "orbits", "definition": "What it orbits.", "domain": "Moon", "range": "Planet"}],
    "attributes": [{"name": "launchYear", "definition": "Year.", "domain": "Mission", "datatype": "string"},
                   {"name": "radius", "definition": "Radius.", "domain": "Planet", "datatype": "decimal"}],
}


def edit(op, kind, term, value=None):
    return {"op": op, "kind": kind, "term": term, "value": value, "reason": "test"}


# --- review ------------------------------------------------------------------------------------


def test_review_edits_apply_and_are_checked():
    d, applied, skipped = review.apply_edits(DRAFT, [
        edit("set_parent", "classes", "SpaceAgency", "Organisation"),
        edit("merge", "classes", "Agency", "SpaceAgency"),
        edit("set_datatype", "attributes", "launchYear", "integer"),
        edit("set_parent", "classes", "Planet", "Moon"),          # a cycle: Moon is under Planet
        edit("set_domain", "relations", "launchedBy", "Rocket"),  # no such class
        edit("set_datatype", "attributes", "radius", "furlongs"),
        edit("drop", "relations", "nothing"),
    ])
    agency = next(c for c in d["classes"] if c["name"] == "SpaceAgency")
    assert agency["parent"] == "Organisation"
    assert {"Agency", "space office"} <= set(agency["synonyms"]) and agency["merged_from"] == ["Agency"]
    assert all(c["name"] != "Agency" for c in d["classes"])
    assert next(r for r in d["relations"] if r["name"] == "launchedBy")["range"] == "SpaceAgency"
    assert next(a for a in d["attributes"] if a["name"] == "launchYear")["datatype"] == "integer"
    assert len(applied) == 3 and len(skipped) == 4
    assert "cycle" in skipped[0]["skipped"] and "Rocket" in skipped[1]["skipped"]
    assert DRAFT["classes"][3]["name"] == "Agency"  # the input is not changed


def test_dropping_a_class_drops_what_depends_on_it_and_lifts_its_children():
    d, applied, _ = review.apply_edits(DRAFT, [edit("drop", "classes", "Planet")])
    assert next(c for c in d["classes"] if c["name"] == "Moon").get("parent") is None
    assert [r["name"] for r in d["relations"]] == ["launchedBy"]
    assert [a["name"] for a in d["attributes"]] == ["launchYear"]
    assert len(applied[0]["effects"]) == 2


def test_discovery_reviews_its_draft_and_reports_it(tmp_path):
    root, lake = _collection_lake(tmp_path, settings={"discovery_min_docs": 3, "discovery_resamples": 1})
    run.run(root, FakeClient, "fake")
    status = get_json(lake, layout.STATUS)
    report = get_json(lake, f"{layout.ONTOLOGY_DRAFTS}/{status['drafts'][0]['draft_id']}/report.json")
    assert [e["op"] for e in report["review"]["applied"]] == ["set_datatype"]
    assert "no class" in report["review"]["skipped"][0]["skipped"]


def test_review_can_be_turned_off(tmp_path):
    root, lake = _collection_lake(tmp_path, settings={"discovery_min_docs": 3, "discovery_resamples": 1,
                                                       "discovery_review": False})
    client = FakeClient()
    run.run(root, lambda: client, "fake")
    assert "review_ontology" not in client.calls


# --- a provided ontology --------------------------------------------------------------------------


def provided_ttl(version: str, label: str = "Missions ontology") -> bytes:
    defn = FakeClient._define({}, "")
    return writer.ontology_ttl(defn, namespace=PROFILE.ontology_base, version=version, label=label).encode()


def test_a_provided_ontology_replaces_discovery(tmp_path):
    root, lake = _collection_lake(tmp_path, settings={"discovery_min_docs": 3})
    lake.put(provided.ONTOLOGY_KEY, provided_ttl("1.0.0"))
    client = FakeClient()
    run.run(root, lambda: client, "fake")
    assert versions.active_version(lake) == "1.0.0"
    assert "propose_types" not in client.calls and "record_knowledge" in client.calls
    m = versions.manifest(lake, "1.0.0")
    assert m["published_by"] == "configuration (ontology_dir)" and "shapes generated" in m["note"]
    assert get_json(lake, layout.STATUS)["stage"] == "ready"
    run.run(root, lambda: client, "fake")  # unchanged: nothing to do
    assert versions.published_versions(lake) == ["1.0.0"]


def test_a_provided_ontology_moves_on_by_version(tmp_path):
    root, lake = _collection_lake(tmp_path, settings={"discovery_min_docs": 3})
    lake.put(provided.ONTOLOGY_KEY, provided_ttl("1.0.0"))
    run.run(root, FakeClient, "fake")
    lake.put(provided.ONTOLOGY_KEY, provided_ttl("1.0.0", label="Renamed"))   # changed, same version
    run.run(root, FakeClient, "fake")
    status = get_json(lake, layout.STATUS)
    assert status["stage"] == "failed" and "bump the version" in status["error"]
    lake.put(provided.ONTOLOGY_KEY, provided_ttl("1.0.1", label="Renamed"))   # a descriptive patch
    run.run(root, FakeClient, "fake")
    assert versions.active_version(lake) == "1.0.1" and versions.manifest(lake, "1.0.1")["kind"] == "descriptive"


def test_a_provided_ontology_is_checked(tmp_path):
    root, lake = _collection_lake(tmp_path)
    lake.put(provided.ONTOLOGY_KEY, provided_ttl("draft"))
    with pytest.raises(ValueError, match="owl:versionInfo"):
        provided.apply(lake)
    lake.put(provided.ONTOLOGY_KEY, b"this is not turtle {")
    with pytest.raises(ValueError, match="does not parse"):
        provided.apply(lake)
    lake.put(provided.ONTOLOGY_KEY, provided_ttl("2.0.0"))
    assert provided.apply(lake)["action"] == "published"
    lake.put(provided.ONTOLOGY_KEY, provided_ttl("1.5.0"))
    with pytest.raises(ValueError, match="older than the active 2.0.0"):
        provided.apply(lake)
