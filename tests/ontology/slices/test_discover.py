"""ontology.slices.discover: propose, aggregate and consolidate a draft ontology from sampled documents."""

import pytest

from knowledge_store.extraction import mapped_doc_ids
from knowledge_store.ingestion.adapters.registry import ingest_source
from knowledge_store.ingestion.slices import refine
from knowledge_store.ontology.domain import model
from knowledge_store.ontology.slices import discover
from knowledge_store.platform_services.adapters.store import LocalStore
from knowledge_store.platform_services.domain import layout
from knowledge_store.platform_services.slices.config import DEFAULT_SOURCES, Profile
from ks_ontology_lake import ScriptedClient

PROFILE = Profile(name="Space", ontology_base="https://example.org/space#")
LONG = "\n\n".join(f"Paragraph {i}. Mission Alpha did thing number {i}, and it went well enough to report." * 4 for i in range(40))


@pytest.fixture
def lake(tmp_path):
    lake = LocalStore(tmp_path / "lake")
    lake.put("landing/a.md", b"# Alpha\n\nMission Alpha was launched by Agency Nova.")
    lake.put("landing/b.md", b"# Beta\n\nMission Beta studies Planet Kiro.")
    ingest_source(lake, DEFAULT_SOURCES[0])
    refine.refine_all(lake, mapped=mapped_doc_ids(lake))
    return lake


def _proposal(name="Mission", text="Mission Alpha", pid=None):
    return {"classes": [{"name": name, "definition": "A flight.", "examples": [{"text": text, "passage_id": pid}]}], "relations": [], "attributes": []}


def test_a_model_that_does_not_call_the_tool_is_an_error():
    with pytest.raises(RuntimeError, match="did not call"):
        discover._call(ScriptedClient(None), "m", "s", "u", discover._define_tool())


def test_the_call_decodes_json_encoded_lists():
    res, usage = discover._call(ScriptedClient({"classes": '[{"name": "A"}]'}), "m", "s", "u", discover._define_tool())
    assert res["classes"] == [{"name": "A"}] and usage == {"inputTokens": 3, "outputTokens": 2}


def test_sample_docs_takes_documents_across_sources(lake):
    ids = discover.sample_docs(lake, 5, seed=1)
    assert len(ids) == 2 and discover.sample_docs(lake, 1, seed=1)[0] in ids


def test_long_documents_are_sampled_to_a_few_passages_keeping_the_first_two(tmp_path):
    lake = LocalStore(tmp_path / "long")
    lake.put("landing/long.md", ("# Long\n\n" + LONG).encode())
    ingest_source(lake, DEFAULT_SOURCES[0])
    refine.refine_all(lake, mapped=mapped_doc_ids(lake))
    (doc_id,) = discover.sample_docs(lake, 1, seed=0)
    ps = discover._passages_for(lake, doc_id, seed=0)
    assert len(ps) == discover.PASSAGES_PER_DOC
    from knowledge_store.ingestion import load_passages

    first_two = [p.passage_id for p in load_passages(lake, doc_id)[:2]]
    assert [p.passage_id for p in ps[:2]] == first_two


def test_propose_keeps_only_terms_with_an_example_found_in_the_passage(lake):
    ids = discover.sample_docs(lake, 1, seed=0)
    from knowledge_store.ingestion import load_passages

    pid = load_passages(lake, ids[0])[0].passage_id
    answer = {"classes": [{"name": "Mission", "examples": [{"text": "MISSION   ", "passage_id": pid}]},
                          {"name": "Ghost", "examples": [{"text": "not in the text", "passage_id": pid}]},
                          {"name": " ", "examples": [{"text": "Mission", "passage_id": pid}]}, "junk"]}
    out, usage = discover.propose(ScriptedClient(answer), "m", lake, ids, PROFILE, seed=0)
    assert [t["name"] for t in out[0]["classes"]] == ["Mission"] and usage["inputTokens"] == 3


def test_a_failed_proposal_skips_the_document(lake):
    ids = discover.sample_docs(lake, 1, seed=0)
    out, _ = discover.propose(ScriptedClient(RuntimeError("boom")), "m", lake, ids, PROFILE, seed=0)
    assert out == []


def test_aggregate_merges_names_counts_documents_and_stability():
    r1 = [{"doc_id": "d1", **_proposal("Space agency", "x")}, {"doc_id": "d2", **_proposal("SpaceAgency", "y")}]
    r2 = [{"doc_id": "d1", "classes": [], "attributes": [], "relations": [
        {"name": "launched by", "subject_type": "Mission", "object_type": "Agency", "examples": [{"text": "z"}]}]}]
    agg = discover.aggregate([r1, r2])
    (agency,) = agg["classes"]
    assert (agency["name"], agency["also"], agency["docs"], agency["stability"]) == ("Space agency", ["SpaceAgency"], 2, 0.5)
    assert agg["relations"][0]["signature"] == "Mission -> Agency"


def test_stability_is_the_mean_overlap_between_rounds():
    a = [{"doc_id": "d", **_proposal("A")}]
    b = [{"doc_id": "d", **_proposal("B")}]
    assert discover.stability_jaccard([a]) is None
    assert discover.stability_jaccard([a, a]) == 1.0 and discover.stability_jaccard([a, b]) == 0.0
    empty = [{"doc_id": "d", "classes": [], "relations": [], "attributes": []}]
    assert discover.stability_jaccard([empty, empty]) == 1.0


def test_discovery_needs_refined_documents(tmp_path):
    with pytest.raises(ValueError, match="ingest and refine first"):
        discover.discover(ScriptedClient(), "m", LocalStore(tmp_path / "empty"), PROFILE)


def _consolidated():
    return {"classes": [{"name": "Mission"}, {"name": "Crewed mission", "parent": "Mission"}], "relations": [], "attributes": []}


def test_discovery_writes_a_reviewed_draft_and_never_activates_it(lake):
    edits = {"edits": [{"op": "drop", "kind": "classes", "term": "Crewed mission", "reason": "noise"}, {"op": "drop", "kind": "classes", "term": "Ghost", "reason": "x"}]}
    rep = discover.discover(ScriptedClient(_proposal(), _proposal(), _consolidated(), edits), "m", lake, PROFILE, sample=2, draft_id="d1")
    assert rep["review"]["applied"][0]["term"] == "Crewed mission" and rep["review"]["skipped"][0]["term"] == "Ghost"
    spec = model.load(data=lake.get(f"{layout.ONTOLOGY_DRAFTS}/d1/ontology.ttl").decode())
    assert set(spec.classes) == {"Mission"} and spec.version == "0.1.0"
    assert lake.exists(f"{layout.ONTOLOGY_DRAFTS}/d1/report.json") and not lake.exists(layout.ONTOLOGY_ACTIVE)


def test_a_failed_review_keeps_the_consolidated_draft(lake):
    rep = discover.discover(ScriptedClient(_proposal(), _proposal(), _consolidated(), RuntimeError("down")), "m", lake, PROFILE, sample=2, draft_id="d2")
    assert "down" in rep["review"]["error"] and rep["counts"]["classes"] == 2


def test_discovery_can_skip_review(lake):
    rep = discover.discover(ScriptedClient(_proposal(), _proposal(), _consolidated()), "m", lake, PROFILE, sample=2, review=False)
    assert rep["review"] is None and rep["draft_id"].startswith("discover-")
