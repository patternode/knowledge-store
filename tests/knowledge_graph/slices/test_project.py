"""Project: gold to the portal's index, for the active version, with what a public caller may see.

The collection is test_review_fixes' `mixed`: five public documents and one private one, run end
to end with the fake model.
"""

from __future__ import annotations

import pytest

from knowledge_store.knowledge_graph.slices import project
from knowledge_store.platform_services.adapters.store import LocalStore
from knowledge_store.platform_services.domain import layout
from knowledge_store.platform_services.ports import get_json, put_json
from test_review_fixes import mixed  # noqa: F401  (fixture)

ZETA = "entity/Mission/mission-zeta"
NOVA = "entity/SpaceAgency/agency-nova"


@pytest.fixture
def built(mixed):  # noqa: F811
    _, lake = mixed
    version = get_json(lake, layout.ONTOLOGY_ACTIVE)["version"]
    return lake, version, lambda name: get_json(lake, layout.index_key(version, name))


def test_nothing_is_projected_without_an_active_version(tmp_path):
    assert project.project(LocalStore(tmp_path)) is None


def test_the_projection_writes_its_five_files_and_returns_the_counts(built):
    lake, version, read = built
    counts = project.project(lake)
    for name in ("summary", "ontology", "entities", "passages", "docs"):
        assert lake.exists(layout.index_key(version, name))
    assert counts == read("summary")["counts"] and counts["entities"] == len(read("entities"))


def test_rebuilding_gives_the_same_entities(built):
    lake, _, read = built
    before = read("entities")
    project.project(lake)
    assert read("entities") == before


def test_an_entity_only_private_text_mentions_is_private(built):
    _, _, read = built
    zeta = next(e for e in read("entities") if e["id"] == ZETA)
    assert zeta["scope"] == "private" and "public" not in zeta


def test_a_public_entity_carries_what_public_documents_say_of_it(built):
    _, _, read = built
    nova = next(e for e in read("entities") if e["id"] == NOVA)
    assert nova["scope"] == "public" and nova["public"]["docs"] < len(nova["docs"])
    assert nova["public"]["links"] < len(nova["out"]) + len(nova["in"])


def test_every_relation_cites_passages_and_is_recorded_at_both_ends(built):
    _, _, read = built
    ents = {e["id"]: e for e in read("entities")}
    for e in ents.values():
        for r in e["out"]:
            assert r["passages"]
            assert any(i["s"] == e["id"] and i["p"] == r["p"] for i in ents[r["o"]]["in"])


def test_passages_carry_their_documents_scope(built):
    _, _, read = built
    passages, docs = read("passages"), read("docs")
    assert {p["scope"] for p in passages.values()} == {"public", "private"}
    assert all(p["scope"] == docs[p["doc"]]["scope"] for p in passages.values())


def test_the_public_counts_are_of_public_text_only(built):
    _, _, read = built
    s = read("summary")
    assert s["public"]["counts"]["documents"] == s["counts"]["documents"] - 1
    assert s["public"]["counts"]["entities"] < s["counts"]["entities"]


def test_the_ontology_file_counts_public_text_and_the_summary_counts_everything(built):
    _, _, read = built
    pub = {c["name"]: c["count"] for c in read("ontology")["classes"]}
    full = read("summary")["ontology_counts"]["classes"]
    assert pub["Mission"] < full["Mission"]


def test_observed_relations_are_counted_by_the_types_at_each_end(built):
    _, _, read = built
    observed = read("summary")["ontology_counts"]["observed"]
    assert any(o["domain"] == "Mission" and o["p"] == "launchedBy" and o["range"] == "SpaceAgency" for o in observed)


def test_a_document_missing_from_silver_is_private(tmp_path):
    assert project.doc_scope("gone", {}, LocalStore(tmp_path)) == "private"
    assert project.doc_scope("known", {"known": {"scope": "public"}}, LocalStore(tmp_path)) == "public"


def test_a_candidate_is_public_when_public_evidence_supports_it(tmp_path):
    docs = {"pub": {"scope": "public"}, "priv": {"scope": "private"}}
    term = {"kind": "class", "term": "Instrument", "evidence": [{"doc_id": "pub"}, {"doc_id": "priv"}]}
    out = project.scoped_candidate(term, docs, LocalStore(tmp_path))
    assert out["scope"] == "public" and [e["scope"] for e in out["evidence"]] == ["public", "private"]
    only = project.scoped_candidate({**term, "evidence": [{"doc_id": "priv"}]}, docs, LocalStore(tmp_path))
    assert only["scope"] == "private"


def test_a_candidate_takes_its_public_name_and_definitions(tmp_path):
    public = {("class", "instrument"): {"names": {"Instruments", "Instrument"}, "docs": {"a", "b"}, "definitions": ["A tool."]}}
    term = {"kind": "class", "term": "instrument kit", "evidence": []}
    out = project.scoped_candidate({**term, "term": "Instrument"}, {}, LocalStore(tmp_path), public)
    assert out["public"] == {"term": "Instrument", "also": ["Instruments"], "definitions": ["A tool."], "docs": 2}


def test_public_terms_read_candidates_from_public_documents_only(tmp_path):
    lake = LocalStore(tmp_path)
    pre = f"{layout.gold_prefix('1.0.0')}/candidates/"
    lake.put(pre + "pub.jsonl", b'{"kind": "class", "term": "Probe", "definition": "A probe."}\n\n'
                                b'{"kind": "class", "term": "probe", "definition": "A probe."}\n')
    lake.put(pre + "priv.jsonl", b'{"kind": "class", "term": "Hush"}\n')
    put_json(lake, layout.doc_key("pub"), {"scope": "public"})
    terms = project.public_terms(lake, "1.0.0", {"priv": {"scope": "private"}})
    assert set(terms) == {("class", "probe")}
    assert terms[("class", "probe")]["names"] == {"Probe", "probe"} and terms[("class", "probe")]["definitions"] == ["A probe."]
