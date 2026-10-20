"""ontology.slices.candidates: the register of terms the ontology lacks, and a revision proposed from it."""

import json

import pytest

from knowledge_store.ontology.slices import candidates
from knowledge_store.platform_services.adapters.store import LocalStore
from knowledge_store.platform_services.domain import layout
from knowledge_store.platform_services.slices.config import Profile
from ks_ontology_lake import ScriptedClient, published

PROFILE = Profile(name="Space", ontology_base="https://example.org/space#")


@pytest.fixture
def lake(tmp_path):
    lake = LocalStore(tmp_path / "lake")
    published(lake, tmp_path)
    return lake


def _seen(lake, doc_id, *rows):
    lake.put(layout.candidates_key("1.2.0", doc_id), ("\n".join(json.dumps(r) for r in rows) + "\n\n").encode())


def _row(term, kind="class", **more):
    return {"kind": kind, "term": term, "definition": f"A {term}.", "evidence": f"the {term}", "passage_ids": ["p1"], **more}


def _request(lake, rid, question, **ontology):
    lake.put(f"{layout.TERM_REQUESTS}/{rid}.json", json.dumps({"id": rid, "question": question, "report": {"ontology": ontology}}).encode())


def test_requested_terms_merge_across_requests_by_kind_and_name(lake):
    _request(lake, "r1", "Which rovers?", classes=[{"name": "Rover", "definition": "A vehicle.", "parent": "Mission"}])
    _request(lake, "r2", "Rovers by year?", classes=[{"name": "rover"}, {"name": " "}], relations=[{"name": "drives", "domain": "Rover"}], other=[{"name": "x"}])
    lake.put(f"{layout.TERM_REQUESTS}/broken.json", b"{not json")
    lake.put(f"{layout.TERM_REQUESTS}/note.txt", b"ignored")
    terms = candidates.requested_terms(lake)
    assert [(t["kind"], t["term"], t["asked"]) for t in terms] == [("class", "Rover", 2), ("relation", "drives", 1)]
    assert terms[0]["questions"] == ["Which rovers?", "Rovers by year?"] and terms[0]["nearest"] == "Mission"
    assert terms[0]["definitions"] == ["A vehicle."] and terms[0]["requests"] == ["r1", "r2"]


def test_the_register_counts_documents_and_marks_terms_a_synonym_covers(lake):
    _seen(lake, "d1", _row("Rover", nearest="Mission"), _row("agency"))
    _seen(lake, "d2", _row("rover", definition="Another."), _row("Rover", nearest="Mission"))
    reg = candidates.build_register(lake, "1.2.0")
    rover, agency = reg["terms"]
    assert (rover["term"], rover["docs"], rover["also"], rover["nearest"], rover["covered_by"]) == ("Rover", 2, ["rover"], "Mission", None)
    assert rover["definitions"] == ["A Rover.", "Another."]
    assert agency["covered_by"] == "SpaceAgency"
    assert reg["documents"] == 2
    assert json.loads(lake.get(layout.CANDIDATE_REGISTER))["version"] == "1.2.0"


def test_requests_join_the_register_even_without_documents(lake):
    _seen(lake, "d1", _row("Rover"))
    _request(lake, "r1", "Which rovers?", classes=[{"name": "Rover", "definition": "A vehicle."}], attributes=[{"name": "mass"}])
    reg = candidates.build_register(lake, "1.2.0")
    by = {t["term"]: t for t in reg["terms"]}
    assert by["Rover"]["asked"] == 1 and by["Rover"]["docs"] == 1 and by["Rover"]["definitions"] == ["A Rover.", "A vehicle."]
    assert by["mass"]["docs"] == 0 and by["mass"]["asked"] == 1


def test_a_revision_needs_an_active_ontology(tmp_path):
    with pytest.raises(ValueError, match="no active ontology"):
        candidates.propose_revision(ScriptedClient(), "m", LocalStore(tmp_path / "empty"), PROFILE)


def test_with_too_little_evidence_there_is_nothing_to_propose(lake):
    _seen(lake, "d1", _row("Rover"))
    out = candidates.propose_revision(ScriptedClient(), "m", lake, PROFILE)
    assert out == {"kind": "revision", "status": "nothing_to_propose", "register_terms": 1}


def test_a_revision_is_a_minor_draft_with_the_new_terms(lake):
    _seen(lake, "d1", _row("Rover"))
    _seen(lake, "d2", _row("Rover"))
    client = ScriptedClient({"classes": [{"name": "Rover", "definition": "A vehicle.", "parent": "Mission"}], "relations": [], "attributes": [], "rejected": [{"name": "x"}]})
    r = candidates.propose_revision(client, "m", lake, PROFILE, draft_id="rev1")
    assert (r["proposed_version"], r["required_bump"], r["diff"]["added"]) == ("1.3.0", "minor", ["Rover"])
    assert r["rejected"] == [{"name": "x"}] and "warning" not in r
    assert lake.exists(f"{layout.ONTOLOGY_DRAFTS}/rev1/ontology.ttl")


def test_a_revision_that_changes_existing_terms_carries_a_warning(tmp_path):
    # A draft is written with one parent per class, so a prior class with two parents loses one:
    # a semantic change the curator must see before publishing.
    from ks_ontology_sample import TTL

    lake = LocalStore(tmp_path / "two-parents")
    published(lake, tmp_path, TTL.replace("o:CrewedMission a owl:Class ; rdfs:subClassOf o:Mission .",
                                          "o:CrewedMission a owl:Class ; rdfs:subClassOf o:Mission, o:Target ."), name="m2")
    _request(lake, "r1", "q", classes=[{"name": "Rover"}])
    r = candidates.propose_revision(ScriptedClient({"classes": [{"name": "Rover"}]}), "m", lake, PROFILE, draft_id="rev2")
    assert r["diff"]["kind"] == "semantic" and "major version" in r["warning"]
