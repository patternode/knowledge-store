"""embed: every silver passage gets a vector in the lake, unchanged passages keep theirs, and
LocalVectorSearch answers from them in the caller's scope, chosen when no Knowledge Base is set."""

from __future__ import annotations

import hashlib
import json
import math
import re

import pytest

from knowledge_store.ingestion import load_passages, silver_doc_ids
from knowledge_store.knowledge_graph.adapters import passages
from knowledge_store.knowledge_graph.adapters.passages import KeywordSearch, KnowledgeBaseSearch, LocalVectorSearch
from knowledge_store.knowledge_graph.slices import embed
from knowledge_store.platform_services.domain import layout
from kg_projection import index_of
from test_review_fixes import mixed  # noqa: F401  (fixture)

DIM = 32


class FakeEmbedder:
    """A bag of hashed words, normalised: texts that share words are close."""

    def __init__(self, model="fake-embed", dimensions=DIM):
        self.model, self.dimensions, self.calls = model, dimensions, []

    def embed(self, texts):
        self.calls.append(list(texts))
        out = []
        for t in texts:
            v = [0.0] * self.dimensions
            for w in re.findall(r"[a-z0-9]+", t.lower()):
                v[int(hashlib.sha256(w.encode()).hexdigest(), 16) % self.dimensions] += 1.0
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
        return out


@pytest.fixture
def embedded(mixed, monkeypatch):  # noqa: F811
    root, lake = mixed
    monkeypatch.delenv("KNOWLEDGE_BASE_ID", raising=False)
    emb = FakeEmbedder()
    monkeypatch.setattr(passages, "embedder_from_env", lambda: emb)
    passages._vectors.clear()
    stats = embed.embed_passages(lake, emb, workers=2)
    return root, lake, emb, stats


def test_every_silver_passage_is_embedded_once(embedded):
    _, lake, emb, stats = embedded
    expected = {p.passage_id for d in silver_doc_ids(lake) for p in load_passages(lake, d)}
    head, rows = embed.read_vectors(lake)
    assert {r["id"] for r in rows} == expected and stats["passages"] == len(expected) == stats["embedded"]
    assert head["model"] == "fake-embed" and head["dim"] == DIM and head["passages"] == len(rows)
    assert all(len(r["vec"]) == DIM and r["scope"] in ("public", "private") and r["text"] for r in rows)
    assert sum(len(c) for c in emb.calls) == len(expected)


def test_a_second_run_by_the_same_model_sends_nothing(embedded):
    _, lake, emb, _ = embedded
    emb.calls.clear()
    stats = embed.embed_passages(lake, emb)
    assert stats["embedded"] == 0 and stats["kept"] == stats["passages"] > 0 and emb.calls == []


def test_another_model_embeds_everything_again(embedded):
    _, lake, _, first = embedded
    other = FakeEmbedder(model="other", dimensions=8)
    stats = embed.embed_passages(lake, other)
    assert stats["embedded"] == first["passages"] and embed.read_vectors(lake)[0]["dim"] == 8


def test_no_vector_file_reads_as_nothing(tmp_path):
    from knowledge_store.platform_services.adapters.store import LocalStore
    assert embed.read_vectors(LocalStore(tmp_path)) == ({}, [])
    assert not passages.has_vectors(LocalStore(tmp_path)) and not passages.has_vectors(None)


def test_local_vector_search_finds_passages_by_meaning_in_scope(embedded):
    _, lake, emb, _ = embedded
    s = LocalVectorSearch(lake, emb)
    assert s.method == "vector"
    hits = s.search("m", "Which agency launched Mission Zeta?", private=True)
    assert hits and any("Zeta" in h["text"] for h in hits)
    assert all(set(h) == {"id", "doc", "title", "text", "score", "source_uri"} for h in hits)
    assert hits == sorted(hits, key=lambda h: h["score"], reverse=True)
    public = s.search("m", "Which agency launched Mission Zeta?", private=False)
    assert public and not any("Zeta" in h["text"] for h in public)
    assert len(s.search("m", "launched", private=True, limit=1)) == 1


def test_the_vectors_are_read_once_a_minute(embedded, monkeypatch):
    _, lake, emb, _ = embedded
    reads = []
    real = embed.read_vectors
    monkeypatch.setattr(passages, "read_vectors", lambda lk: (reads.append(1), real(lk))[1])
    passages._vectors.clear()
    s = LocalVectorSearch(lake, emb)
    s.search("m", "launched", private=True)
    s.search("m", "launched", private=True)
    assert len(reads) == 1


def test_local_vectors_are_chosen_without_a_knowledge_base_and_yield_to_one(embedded, monkeypatch, tmp_path):
    root, lake, _, _ = embedded
    assert isinstance(passages.passage_search(None, lake), LocalVectorSearch)
    assert isinstance(passages.passage_search(index_of(tmp_path), lake), LocalVectorSearch)
    assert isinstance(passages.passage_search(index_of(tmp_path)), KeywordSearch)
    monkeypatch.setenv("KNOWLEDGE_BASE_ID", "kb-1")
    assert isinstance(passages.passage_search(None, lake), KnowledgeBaseSearch)


def test_search_through_the_gateway_says_vector_and_reads_a_hit_back(embedded):
    root, lake, _, _ = embedded
    from knowledge_store.knowledge_graph.adapters import gateway
    out = gateway.call(root, "search_passages", {"collection": "m", "query": "Mission Zeta", "caller_private": True})
    assert out["method"] == "vector" and out["passages"]
    hit = out["passages"][0]
    read = gateway.call(root, "read_passages", {"collection": "m", "ids": [hit["id"]], "caller_private": True})
    assert read["passages"][0]["text"] == hit["text"]


def test_the_vector_file_is_the_layout_key(embedded):
    _, lake, _, _ = embedded
    assert lake.exists(layout.SILVER_VECTORS)
    first = lake.get(layout.SILVER_VECTORS).decode().splitlines()[0]
    assert json.loads(first)["model"] == "fake-embed"


# --- the Titan adapter, against a fake Bedrock client ----------------------------------------------


class FakeBedrock:
    def __init__(self):
        self.calls = []

    def invoke_model(self, *, modelId, body):
        import io
        self.calls.append((modelId, json.loads(body)))
        return {"body": io.BytesIO(json.dumps({"embedding": [0.6, 0.8], "inputTextTokenCount": 3}).encode())}


def test_titan_sends_each_text_normalised_at_the_asked_dimensions(monkeypatch):
    from knowledge_store.knowledge_graph.adapters.embeddings import TitanEmbedder, embedder_from_env, DEFAULT_MODEL
    fake = FakeBedrock()
    t = TitanEmbedder("amazon.titan-embed-text-v2:0", dimensions=2, client=fake)
    assert t.embed(["a", "b" * 50_000]) == [[0.6, 0.8], [0.6, 0.8]]
    assert [c[0] for c in fake.calls] == ["amazon.titan-embed-text-v2:0"] * 2
    assert fake.calls[0][1] == {"inputText": "a", "dimensions": 2, "normalize": True}
    assert len(fake.calls[1][1]["inputText"]) == 40_000
    monkeypatch.delenv("EMBEDDING_MODEL_ID", raising=False)
    assert embedder_from_env().model == DEFAULT_MODEL and embedder_from_env().dimensions == 1024
    monkeypatch.setenv("EMBEDDING_MODEL_ID", "other-model")
    assert embedder_from_env().model == "other-model"
