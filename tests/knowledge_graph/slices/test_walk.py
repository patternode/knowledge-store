"""walk: the graph built from a lake's open facts and vectors finds, for a question, the passages
connected to it across documents, in the caller's scope; and says so when there is no walk."""
from __future__ import annotations

import json
import sys

import pytest

from knowledge_store.extraction.slices import open_facts
from knowledge_store.ingestion.slices.ingest import ingest
from knowledge_store.ingestion.slices.refine import load_doc, load_passages, refine_all, silver_doc_ids
from knowledge_store.knowledge_graph.slices import embed, walk
from knowledge_store.platform_services import SourceConfig, layout
from knowledge_store.platform_services.adapters.store import LocalStore
from test_embed import FakeEmbedder
from test_ingest import FakeSource
from test_open_facts import TripleClient

DOCS = {
    "alpha.md": "# Alpha\n\nMission Alpha was launched by Agency Nova in 2011.\n\nIts cruise lasted seven months.",
    "nova.md": "# Nova\n\nAgency Nova is based in Lyon.\n\nIts campus opened in 1990 beside the river.",
    "beta.md": "# Beta\n\nMission Beta was launched by Agency Orbis in 2014.\n\nIts cruise lasted nine months.",
    "orbis.md": "# Orbis\n\nAgency Orbis is based in Turin.\n\nIts campus opened in 1985 near the hills.",
}


class HopClient(TripleClient):
    """record_facts for the sentences above: launches and the agencies' seats."""

    def converse(self, **kw):
        self.calls.append(kw)
        text = kw["messages"][0]["content"][0]["text"]
        facts, pid = [], None
        for line in text.splitlines():
            if line.startswith('<passage id="'):
                pid = line.split('"')[1]
            elif pid and " was launched by " in line:
                s, rest = line.split(" was launched by ")
                facts.append({"subject": s, "predicate": "launched by", "object": rest.split(" in ")[0], "passage": pid})
            elif pid and " is based in " in line:
                s, o = line.rstrip(".").split(" is based in ")
                facts.append({"subject": s, "predicate": "based in", "object": o, "passage": pid})
        return {"output": {"message": {"content": [{"toolUse": {"name": "record_facts", "input": {"facts": facts}}}]}},
                "stopReason": "tool_use", "usage": {"inputTokens": 10, "outputTokens": 5}}


@pytest.fixture
def lake(tmp_path):
    lake = LocalStore(tmp_path / "lake")
    ingest(lake, SourceConfig("docs", "fake"), FakeSource({k: ("1", v.encode()) for k, v in DOCS.items()}))
    refine_all(lake)
    emb = FakeEmbedder()
    embed.embed_passages(lake, emb, workers=1)
    open_facts.extract_open_facts(lake, HopClient(), "fake", workers=1)
    walk._cache.clear()
    return lake


def _pid(lake, title):
    doc_id = next(d for d in silver_doc_ids(lake) if load_doc(lake, d)["title"] == title)
    return load_passages(lake, doc_id)[0].passage_id


def test_the_walk_is_built_from_the_facts_and_the_vectors(lake):
    emb = FakeEmbedder()
    out = walk.build_walk(lake, emb, workers=2)
    assert out["facts"] == 4 and out["passages"] == 4 and out["phrases"] == 6 and out["model"] == "fake-embed"
    g = json.loads(lake.get(layout.WALK_GRAPH))
    assert set(g["phrases"]) == {"mission alpha", "agency nova", "mission beta", "agency orbis", "lyon", "turin"}
    rows = [json.loads(l) for l in lake.get(layout.WALK_VECTORS).decode().splitlines()]
    assert rows[0]["facts"] == 4 and {r["kind"] for r in rows[1:]} == {"fact", "phrase"}
    assert all(len(r["vec"]) == emb.dimensions for r in rows[1:])
    assert sum(len(c) for c in emb.calls) == 4 + 6   # every fact and every phrase embedded once


def test_related_passages_cross_from_the_mission_to_its_agencys_seat(lake):
    emb = FakeEmbedder()
    walk.build_walk(lake, emb)
    out = walk.related(lake, "Where is the agency that launched Mission Alpha based?", embedder=emb, limit=3)
    ids = [p["id"] for p in out["passages"]]
    assert out["method"] == "walk" and _pid(lake, "Nova") in ids and _pid(lake, "Alpha") in ids
    assert ids.index(_pid(lake, "Nova")) < ids.index(_pid(lake, "Beta")) if _pid(lake, "Beta") in ids else True
    assert all(p["text"] and p["doc"] and p["title"] for p in out["passages"])
    assert any("Mission Alpha launched by Agency Nova" == v["fact"] for v in out["via"])


def test_the_limit_is_capped_and_a_keep_filter_narrows_the_seeds(lake):
    emb = FakeEmbedder()
    walk.build_walk(lake, emb)
    seen = {}

    def keep(question, facts):
        seen["facts"] = [f["s"] for f in facts]
        return [f["s"] == "Mission Beta" for f in facts]
    out = walk.related(lake, "Mission Alpha Mission Beta agency", embedder=emb, limit=99, keep=keep)
    assert len(out["passages"]) <= 15 and seen["facts"]
    assert [v["fact"] for v in out["via"]] == ["Mission Beta launched by Agency Orbis"]
    none = walk.related(lake, "Mission Alpha", embedder=emb, keep=lambda q, f: [False] * len(f))
    assert none["via"]   # a filter that keeps nothing is ignored rather than leaving no seed


def test_private_passages_never_seed_or_surface_for_a_public_caller(lake):
    emb = FakeEmbedder()
    nova = _pid(lake, "Nova")
    head, rows = embed.read_vectors(lake)
    for r in rows:
        if r["id"] == nova:
            r["scope"] = "private"
    lake.put(layout.SILVER_VECTORS, ("\n".join(json.dumps(x) for x in [head, *rows]) + "\n").encode())
    walk.build_walk(lake, emb)
    public = walk.related(lake, "Where is Agency Nova based?", embedder=emb, private=False)
    private = walk.related(lake, "Where is Agency Nova based?", embedder=emb, private=True)
    assert nova not in {p["id"] for p in public["passages"]} and all(v["passage"] != nova for v in public["via"])
    assert nova in {p["id"] for p in private["passages"]}


def test_without_a_walk_the_tool_says_what_to_run(lake):
    assert not walk.has_walk(lake) and "knowledge-store facts" in walk.related(lake, "q", embedder=FakeEmbedder())["error"]


def test_synonym_pairs_link_close_phrases_with_or_without_numpy(monkeypatch):
    vecs = [[1.0, 0.0], [0.99, 0.14], [0.0, 1.0]]
    with_numpy = walk.synonym_pairs(["a", "a2", "b"], vecs, threshold=0.9)
    monkeypatch.setitem(sys.modules, "numpy", None)
    without = walk.synonym_pairs(["a", "a2", "b"], vecs, threshold=0.9)
    assert with_numpy == without and [(a, b) for a, b, _ in without] == [("a", "a2")]
    assert walk.synonym_pairs(["a"], [[1.0]]) == []


def test_a_second_build_reuses_the_vectors_of_the_first(lake):
    emb = FakeEmbedder()
    first = walk.build_walk(lake, emb)
    assert first["reused"] == 0 and sum(len(c) for c in emb.calls) == 10
    again = walk.build_walk(lake, emb)
    assert again["reused"] == 10 and sum(len(c) for c in emb.calls) == 10   # nothing was sent again
    other = FakeEmbedder(model="other-model")
    assert walk.build_walk(lake, other)["reused"] == 0                      # a new model embeds everything


def test_a_failed_build_leaves_a_checkpoint_the_next_one_resumes_from(lake, monkeypatch):
    monkeypatch.setattr(walk, "CHECKPOINT_EVERY", 1)
    monkeypatch.setattr(walk.time, "sleep", lambda s: None)

    class Flaky(FakeEmbedder):
        """Fails its first call, then works: the batch is retried and the build completes."""
        failures = 0

        def embed(self, texts):
            if self.failures < 1:
                self.failures += 1
                raise RuntimeError("ModelErrorException: try again")
            return super().embed(texts)
    emb = Flaky()
    assert walk.build_walk(lake, emb, workers=1)["facts"] == 4 and emb.failures == 1

    class DiesOnPhrases(FakeEmbedder):
        """Embeds the facts, then dies: the checkpoint holds the facts' vectors."""
        def embed(self, texts):
            if any(" " in x and x.split()[0] == "Mission" or x.startswith("Agency") for x in texts) and len(self.calls) >= 1:
                raise RuntimeError("down")
            return super().embed(texts)
    monkeypatch.setattr(walk, "EMBED_ATTEMPTS", 2)
    lake.delete(layout.WALK_VECTORS)
    with pytest.raises(RuntimeError):
        walk.build_walk(lake, DiesOnPhrases(), workers=1)
    rows = [json.loads(l) for l in lake.get(layout.WALK_VECTORS).decode().splitlines()]
    assert rows[0]["checkpoint"] and len(rows) - 1 == 4 and all(r["kind"] == "checkpoint" for r in rows[1:])
    resumed = FakeEmbedder()
    out = walk.build_walk(lake, resumed, workers=1)
    assert out["reused"] == 4 and sum(len(c) for c in resumed.calls) == 6     # only the phrases were sent
    assert walk.related(lake, "Where is Agency Nova based?", embedder=resumed)["passages"]


def test_the_walk_is_cached_until_it_is_rebuilt(lake):
    emb = FakeEmbedder()
    walk.build_walk(lake, emb)
    first = walk.load_walk(lake)
    assert walk.load_walk(lake) is first
    walk.build_walk(lake, emb)
    assert walk.load_walk(lake) is not first


def test_keep_with_model_parses_the_numbers_and_tolerates_failure():
    class Model:
        def converse(self, **kw):
            return {"output": {"message": {"content": [{"text": "Facts 2 and 3 help."}]}}}

    class Broken:
        def converse(self, **kw):
            raise RuntimeError("down")
    facts = [{"s": "a", "p": "b", "o": "c"}] * 3
    assert walk.keep_with_model(Model(), "m")("q", facts) == [False, True, True]
    assert walk.keep_with_model(Broken(), "m")("q", facts) == [True, True, True]

    class Silent:
        def converse(self, **kw):
            return {"output": {"message": {"content": [{"text": "none"}]}}}
    assert walk.keep_with_model(Silent(), "m")("q", facts) == [True, True, True]
