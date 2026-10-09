"""The whole lifecycle offline: upload -> bronze -> silver -> discovery -> curated publish ->
extraction -> candidates -> additive revision -> delta extraction -> projection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fake_llm import FakeClient
from knowledge_store import layout
from knowledge_store.config import Profile
from knowledge_store.ontology import candidates, discover, model, versions
from knowledge_store.pipeline import extract, project, refine, run
from knowledge_store.pipeline.ingest import ingest_source
from knowledge_store.config import DEFAULT_SOURCES
from knowledge_store.store import LocalStore, put_json

DOCS = {
    "a.md": "# Alpha\n\nMission Alpha was launched by Agency Nova in 2011.\n\nMission Alpha studies Planet Kiro.",
    "b.txt": "Beta report\n\nMission Beta was launched by Agency Orbis in 2014.\n\nMission Beta carries Instrument Lux "
             "and studies Planet Vey.",
    "c.html": "<html><head><title>Gamma</title></head><body><p>Mission Gamma was launched by Agency Nova in 2019.</p>"
              "<p>Mission Gamma carries Instrument Mira.</p></body></html>",
    "d.json": json.dumps({"title": "Delta", "summary": "Mission Delta was launched by Agency Orbis in 2021.",
                          "notes": "Mission Delta studies Planet Kiro."}),
    "e.md": "# Epsilon\n\nMission Epsilon was launched by Agency Nova in 2023. Mission Epsilon studies Planet Vey.",
}


@pytest.fixture
def lake(tmp_path):
    lake = LocalStore(tmp_path / "lake")
    for name, body in DOCS.items():
        lake.put(f"landing/{name}", body.encode())
    return lake


PROFILE = Profile(name="Missions", description="Space missions.", key_terms=("mission", "agency"),
                  ontology_base="https://example.org/ontology/missions#")


def _publish_draft(lake, draft_id, tmp_path, version=None) -> Path:
    d = tmp_path / f"curated-{draft_id}"
    d.mkdir()
    for n in ("ontology.ttl", "shapes.ttl"):
        body = lake.get(f"{layout.ONTOLOGY_DRAFTS}/{draft_id}/{n}").decode()
        if version and n == "ontology.ttl":
            body = body.replace('owl:versionInfo "0.1.0"', f'owl:versionInfo "{version}"')
        (d / n).write_text(body)
    return d


def test_ingest_is_content_addressed_and_idempotent(lake):
    stats, _ = ingest_source(lake, DEFAULT_SOURCES[0])
    assert stats.stored == 5
    again, _ = ingest_source(lake, DEFAULT_SOURCES[0])
    assert again.skipped == 5 and again.stored == 0
    lake.put("landing/copy-of-a.md", DOCS["a.md"].encode())
    dup, _ = ingest_source(lake, DEFAULT_SOURCES[0])
    assert dup.duplicate == 1 and dup.stored == 0


def test_refine_parses_every_format(lake):
    ingest_source(lake, DEFAULT_SOURCES[0])
    rows = refine.refine_all(lake)
    assert {r["status"] for r in rows} == {"refined"}
    titles = {refine.load_doc(lake, d)["title"] for d in refine.silver_doc_ids(lake)}
    assert {"Alpha", "Gamma", "Delta"} <= titles
    assert refine.refine_all(lake) == []


def test_full_lifecycle(lake, tmp_path):
    client = FakeClient()
    ingest_source(lake, DEFAULT_SOURCES[0])
    refine.refine_all(lake)

    # 1. discovery -> draft, never active by itself
    rep = discover.discover(client, "fake", lake, PROFILE, sample=5, resamples=2)
    assert rep["counts"]["classes"] == 3 and versions.active_version(lake) is None
    assert rep["stability_jaccard"]["classes"] is not None
    spec = model.load(data=lake.get(f"{layout.ONTOLOGY_DRAFTS}/{rep['draft_id']}/ontology.ttl").decode())
    assert set(spec.classes) == {"Mission", "SpaceAgency", "TargetBody"}
    assert spec.relations["launchedBy"].range == ("SpaceAgency",)
    assert spec.attributes["launchYear"].range == ("integer",)

    # 2. a person publishes it
    curated = _publish_draft(lake, rep["draft_id"], tmp_path)
    m = versions.publish(lake, curated, by="test", activate=True)
    assert m["kind"] == "initial" and versions.active_version(lake) == "0.1.0"
    with pytest.raises(ValueError, match="immutable"):
        versions.publish(lake, curated, by="test")

    # 3. extraction at 0.1.0, with candidates for the unknown Instrument
    rows = extract.extract_all(lake, client, "fake", PROFILE, workers=2)
    assert {r["status"] for r in rows} == {"extracted"}, rows
    assert extract.extract_all(lake, client, "fake", PROFILE) == []
    reg = candidates.build_register(lake, "0.1.0")
    inst = next(t for t in reg["terms"] if t["term"] == "Instrument")
    assert inst["docs"] == 2 and inst["covered_by"] is None

    # 4. a revision from the register: additive, so a minor bump
    rev = candidates.propose_revision(client, "fake", lake, PROFILE, min_docs=2)
    assert rev["diff"]["kind"] == "additive" and rev["proposed_version"] == "0.2.0"
    assert set(rev["diff"]["added"]) == {"Instrument", "carries"}
    d2 = tmp_path / "v020"
    d2.mkdir()
    for n in ("ontology.ttl", "shapes.ttl"):
        (d2 / n).write_bytes(lake.get(f"{layout.ONTOLOGY_DRAFTS}/{rev['draft_id']}/{n}"))
    m2 = versions.publish(lake, d2, by="test", activate=True)
    assert m2["kind"] == "additive" and m2["base"] == "0.1.0"
    assert versions.chain(lake, "0.2.0") == ["0.2.0", "0.1.0"]

    # 5. delta extraction: only documents that mention the new terms, extending known entities
    rows = extract.extract_all(lake, client, "fake", PROFILE)
    done = {refine.load_doc(lake, r["doc_id"])["title"]: r["status"] for r in rows}
    assert done["Beta report"] == "extracted" and done["Gamma"] == "extracted"
    assert done["Alpha"] == "not_selected"
    delta = json.loads(lake.get(layout.extraction_key("0.2.0", next(r["doc_id"] for r in rows
                                                                     if r["status"] == "extracted"))))
    assert delta["delta"] and all(e["type"] == "Instrument" for e in delta["result"]["entities"])

    # 6. projection over the chain: old facts and new ones together
    counts = project.project(lake)
    ents = json.loads(lake.get(layout.index_key("0.2.0", "entities")))
    beta = next(e for e in ents if e["label"] == "Mission Beta")
    assert {r["p"] for r in beta["out"]} == {"launchedBy", "studies", "carries"}
    assert any(a["p"] == "launchYear" and a["v"] == "2014" for a in beta["attributes"])
    nova = next(e for e in ents if e["label"] == "Agency Nova")
    assert len(nova["docs"]) == 3  # one node across documents
    assert counts["entities"] == len(ents)
    onto = json.loads(lake.get(layout.index_key("0.2.0", "ontology")))
    seen = {(o["domain"], o["p"], o["range"]): o["count"] for o in onto["observed"]}
    assert seen[("Mission", "launchedBy", "SpaceAgency")] >= 1


def test_semantic_change_needs_major(lake, tmp_path):
    ttl = """@prefix o: <https://example.org/o#> . @prefix owl: <http://www.w3.org/2002/07/owl#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    <https://example.org/o> a owl:Ontology ; owl:versionInfo "{v}" .
    o:A a owl:Class . o:B a owl:Class {extra} .
    """
    d1, d2, d3 = (tmp_path / n for n in ("1", "2", "3"))
    for d, v, extra in ((d1, "1.0.0", ""), (d2, "1.1.0", "; rdfs:subClassOf o:A"), (d3, "2.0.0", "; rdfs:subClassOf o:A")):
        d.mkdir()
        (d / "ontology.ttl").write_text(ttl.format(v=v, extra=extra))
    versions.publish(lake, d1, activate=True)
    with pytest.raises(ValueError, match="needs a major bump"):
        versions.publish(lake, d2)
    assert versions.publish(lake, d3, activate=True)["kind"] == "semantic"
    assert versions.chain(lake, "2.0.0") == ["2.0.0"]


def _collection_lake(tmp_path, cid="default", settings=None):
    from knowledge_store import collections
    root = LocalStore(tmp_path / "root")
    for name, body in DOCS.items():
        root.put(f"landing/{cid}/{name}", body.encode())
    lake = collections.scoped(root, cid)
    put_json(lake, layout.CONFIG_SETTINGS, settings or {})
    put_json(lake, layout.CONFIG_PROFILE, PROFILE.to_dict())
    return root, lake


def test_sweep_auto_mode_goes_end_to_end(tmp_path):
    root, lake = _collection_lake(tmp_path, settings={"ontology_mode": "auto", "discovery_min_docs": 3,
                                                       "discovery_resamples": 1})
    client = FakeClient()
    out = run.run(root, lambda: client, "fake")
    assert out["default"] and versions.active_version(lake) == "0.1.0"
    assert json.loads(lake.get(layout.STATUS))["stage"] == "ready"
    assert lake.exists(layout.index_key("0.1.0", "summary"))
    assert not root.exists(layout.PIPELINE_LOCK)


def test_sweep_curated_mode_waits(tmp_path):
    root, lake = _collection_lake(tmp_path, settings={"discovery_min_docs": 3, "discovery_resamples": 1})
    run.run(root, FakeClient, "fake")
    assert versions.active_version(lake) is None
    assert json.loads(lake.get(layout.STATUS))["stage"] == "awaiting_curation"


def test_collections_are_separate(tmp_path):
    from knowledge_store import collections
    root, a = _collection_lake(tmp_path, "missions", {"ontology_mode": "auto", "discovery_min_docs": 3,
                                                      "discovery_resamples": 1})
    root.put("landing/notes/n1.md", b"# Shopping\n\nBuy apples and pears for the week ahead, and some bread.")
    put_json(root, collections.CONFIG, [{"id": "missions"}, {"id": "notes"}])
    b = collections.scoped(root, "notes")
    put_json(b, layout.CONFIG_SETTINGS, {"discovery_min_docs": 3})
    out = run.run(root, FakeClient, "fake")
    assert set(out) == {"missions", "notes"}
    assert versions.active_version(a) == "0.1.0" and versions.active_version(b) is None
    assert len(list(a.list("silver/documents/"))) == 5 and len(list(b.list("silver/documents/"))) == 1
    assert json.loads(b.get(layout.STATUS))["stage"] == "waiting_for_documents"
    assert all(k.startswith(("collections/", "landing/", "config/")) for k in root.list(""))


def test_lock_is_exclusive(lake):
    assert run.acquire(lake, "a") and not run.acquire(lake, "b")
    run.release(lake)
    assert run.acquire(lake, "b")


def test_release_renders_every_target(lake, tmp_path):
    client = FakeClient()
    ingest_source(lake, DEFAULT_SOURCES[0])
    refine.refine_all(lake)
    rep = discover.discover(client, "fake", lake, PROFILE, sample=5, resamples=1)
    m = versions.publish(lake, _publish_draft(lake, rep["draft_id"], tmp_path), activate=True)
    assert set(m["renditions"]) >= {"owl/ontology.ttl", "owl/shapes.ttl", "agent/ontology.md", "agent/ontology.json",
                                    "neo4j/schema.cypher", "neo4j/mapping.json", "neo4j/schema.md",
                                    "extraction/tool.json", "jsonld/context.jsonld"}
    pre = layout.ontology_version_prefix("0.1.0") + "/renditions"
    mapping = json.loads(lake.get(f"{pre}/neo4j/mapping.json"))
    assert mapping["relationships"]["launchedBy"]["type"] == "LAUNCHED_BY"
    assert "(:Mission)-[:LAUNCHED_BY]->(:SpaceAgency)" in lake.get(f"{pre}/neo4j/schema.md").decode()
    agent = json.loads(lake.get(f"{pre}/agent/ontology.json"))
    assert {t["name"] for t in agent["types"]} == {"Mission", "SpaceAgency", "TargetBody"}
    tool = json.loads(lake.get(f"{pre}/extraction/tool.json"))
    assert tool["toolSpec"]["name"] == "record_knowledge"


class StringifyingClient(FakeClient):
    """Answers proposals the way models sometimes do: each list sent as a string of its JSON,
    with a stray non-object item in it."""

    def converse(self, **kw):
        resp = super().converse(**kw)
        if kw["toolConfig"]["tools"][0]["toolSpec"]["name"] == "propose_types":
            tu = resp["output"]["message"]["content"][0]["toolUse"]
            tu["input"] = {k: json.dumps((v or []) + ["stray"]) for k, v in tu["input"].items()}
        return resp


def test_discovery_survives_json_encoded_proposals(lake):
    ingest_source(lake, DEFAULT_SOURCES[0])
    refine.refine_all(lake)
    rep = discover.discover(StringifyingClient(), "fake", lake, PROFILE, sample=5, resamples=2)
    spec = model.load(data=lake.get(f"{layout.ONTOLOGY_DRAFTS}/{rep['draft_id']}/ontology.ttl").decode())
    assert set(spec.classes) == {"Mission", "SpaceAgency", "TargetBody"}


def test_version_iri_must_name_the_version(lake, tmp_path):
    """A draft's owl:versionIRI names the draft's version; a curator who bumps only
    owl:versionInfo would publish a version whose IRI names another. Publish refuses it."""
    ttl = """@prefix o: <https://example.org/o#> . @prefix owl: <http://www.w3.org/2002/07/owl#> .
    <https://example.org/o> a owl:Ontology ; owl:versionInfo "1.0.0" ;
        owl:versionIRI <https://example.org/o/{iri}> .
    o:A a owl:Class .
    """
    bad, good = tmp_path / "bad", tmp_path / "good"
    for d, iri in ((bad, "0.1.0"), (good, "1.0.0")):
        d.mkdir()
        (d / "ontology.ttl").write_text(ttl.format(iri=iri))
    with pytest.raises(ValueError, match="does not name version 1.0.0"):
        versions.publish(lake, bad)
    assert versions.publish(lake, good)["version"] == "1.0.0"


def test_a_header_only_change_is_a_patch(lake, tmp_path):
    """Correcting the ontology's own comment (or label) is descriptive: publishable as a patch,
    with nothing to re-extract, rather than refused as identical."""
    ttl = """@prefix o: <https://example.org/o#> . @prefix owl: <http://www.w3.org/2002/07/owl#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    <https://example.org/o> a owl:Ontology ; owl:versionInfo "{v}" ; rdfs:comment "{c}" .
    o:A a owl:Class .
    """
    d1, d2, d3 = (tmp_path / n for n in ("1", "2", "3"))
    for d, v, c in ((d1, "1.0.0", "draft"), (d2, "1.0.1", "curated"), (d3, "1.0.2", "curated")):
        d.mkdir()
        (d / "ontology.ttl").write_text(ttl.format(v=v, c=c))
    versions.publish(lake, d1, activate=True)
    m = versions.publish(lake, d2, activate=True)
    assert m["kind"] == "descriptive" and m["base"] == "1.0.0"
    with pytest.raises(ValueError, match="identical"):
        versions.publish(lake, d3)
