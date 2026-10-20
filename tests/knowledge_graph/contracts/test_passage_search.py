"""PassageSearch: every adapter searches one collection's passages in the caller's scope.

The keyword adapter reads the projection; the Knowledge Base adapter runs against a fake
bedrock-agent-runtime client that holds the same passages and applies the filter it is sent.
"""

from __future__ import annotations

import pytest

from knowledge_store.ingestion import load_doc, load_passages, silver_doc_ids
from knowledge_store.knowledge_graph.adapters import passages
from knowledge_store.knowledge_graph.adapters.passages import KeywordSearch, KnowledgeBaseSearch
from knowledge_store.knowledge_graph.ports import PassageSearch
from kg_projection import PASSAGES, index_of
from test_review_fixes import mixed  # noqa: F401  (fixture)


def _matches(flt: dict, md: dict) -> bool:
    if "andAll" in flt:
        return all(_matches(f, md) for f in flt["andAll"])
    return md.get(flt["equals"]["key"]) == flt["equals"]["value"]


class FakeKnowledgeBase:
    """retrieve() over the projection's passages, plus one from another collection."""

    def __init__(self, honour_filter: bool = True):
        self.honour_filter = honour_filter
        self.requests: list[dict] = []
        self.hits = [{"content": {"text": p["text"]}, "score": 0.91234,
                      "metadata": {"collection": "m", "passage_id": pid, "doc": p["doc"], "scope": p["scope"], "title": "T"}}
                     for pid, p in PASSAGES.items()]
        self.hits.append({"content": {"text": "launched elsewhere"}, "score": 0.5,
                          "metadata": {"collection": "other", "passage_id": "x", "scope": "public"}})

    def retrieve(self, **kw):
        self.requests.append(kw)
        flt = kw["retrievalConfiguration"]["vectorSearchConfiguration"]["filter"]
        n = kw["retrievalConfiguration"]["vectorSearchConfiguration"]["numberOfResults"]
        hits = [h for h in self.hits if not self.honour_filter or _matches(flt, h["metadata"])]
        return {"retrievalResults": hits[:n]}


@pytest.fixture(params=["keyword", "vector"])
def search(request, tmp_path, monkeypatch) -> PassageSearch:
    monkeypatch.setenv("KNOWLEDGE_BASE_ID", "kb-1")
    if request.param == "keyword":
        return KeywordSearch(index_of(tmp_path))
    return KnowledgeBaseSearch(FakeKnowledgeBase())


def test_an_adapter_names_its_method(search):
    assert search.method in ("keyword", "vector")


def test_a_search_returns_passages_with_their_ids_documents_and_text(search):
    hits = search.search("m", "launched", private=True)
    assert {h["id"] for h in hits} == set(PASSAGES)
    assert all(h["doc"] and h["text"] for h in hits)


def test_a_public_caller_never_gets_a_private_passage(search):
    assert [h["id"] for h in search.search("m", "launched", private=False)] == ["p-pub"]


def test_the_limit_caps_the_hits(search):
    assert len(search.search("m", "launched", private=True, limit=1)) == 1


# --- the Knowledge Base adapter's own rules ------------------------------------------------------


def test_the_knowledge_base_is_asked_for_the_collection_and_for_public_passages(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_BASE_ID", "kb-1")
    kb = FakeKnowledgeBase()
    KnowledgeBaseSearch(kb).search("m", "x" * 2000, private=False, limit=3)
    req = kb.requests[0]
    assert req["knowledgeBaseId"] == "kb-1" and len(req["retrievalQuery"]["text"]) == 1000
    assert req["retrievalConfiguration"]["vectorSearchConfiguration"] == {"numberOfResults": 3, "filter": {"andAll": [
        {"equals": {"key": "collection", "value": "m"}}, {"equals": {"key": "scope", "value": "public"}}]}}


def test_a_hit_the_filter_should_have_removed_is_dropped_anyway(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_BASE_ID", "kb-1")
    hits = KnowledgeBaseSearch(FakeKnowledgeBase(honour_filter=False)).search("m", "launched", private=False)
    assert [h["id"] for h in hits] == ["p-pub"]


def test_a_knowledge_base_hit_carries_a_rounded_score_and_no_empty_source():
    hit = passages.kb_search("m", "q", private=True, client=FakeKnowledgeBase())[0]
    assert hit["score"] == 0.9123 and hit["source_uri"] is None and hit["title"] == "T"


# --- choosing and reading -----------------------------------------------------------------------


def test_the_knowledge_base_is_used_when_one_is_configured(monkeypatch, tmp_path):
    monkeypatch.setenv("KNOWLEDGE_BASE_ID", "kb-1")
    assert isinstance(passages.passage_search(index_of(tmp_path)), KnowledgeBaseSearch)


def test_keyword_search_is_used_without_a_knowledge_base(monkeypatch, tmp_path):
    monkeypatch.delenv("KNOWLEDGE_BASE_ID", raising=False)
    assert isinstance(passages.passage_search(index_of(tmp_path)), KeywordSearch)
    assert passages.passage_search(None) is None


def test_search_without_a_projection_is_an_error(monkeypatch, tmp_path):
    monkeypatch.delenv("KNOWLEDGE_BASE_ID", raising=False)
    assert "no knowledge graph yet" in passages.search(None, None, "m", "q", private=True)["error"]


def test_search_says_which_method_answered(monkeypatch, tmp_path):
    monkeypatch.delenv("KNOWLEDGE_BASE_ID", raising=False)
    out = passages.search(None, index_of(tmp_path), "m", "launched", private=False)
    assert out["method"] == "keyword" and [p["id"] for p in out["passages"]] == ["p-pub"]


def test_read_takes_passages_from_the_projection_in_order_and_once(tmp_path):
    idx = index_of(tmp_path)
    out = passages.read(idx.lake, idx, ["p-priv", "p-pub", "p-pub", 5], private=True)
    assert [p["id"] for p in out] == ["p-priv", "p-pub"] and out[1]["name"] == "public.md"


def test_read_falls_back_to_silver_for_an_uncited_passage_in_scope(mixed):  # noqa: F811
    _, lake = mixed
    by_scope = {}
    for d in silver_doc_ids(lake):
        by_scope.setdefault(load_doc(lake, d).get("scope", "public"), []).append(load_passages(lake, d)[0].passage_id)
    pub, priv = by_scope["public"][0], by_scope["private"][0]
    assert [p["id"] for p in passages.read(lake, None, [pub, priv], private=True)] == [pub, priv]
    assert [p["id"] for p in passages.read(lake, None, [pub, priv], private=False)] == [pub]
    assert passages.from_silver(lake, ["0" * 40], private=True) == []
