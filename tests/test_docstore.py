"""The portal's projection in a document store answers exactly as the in-memory index does.

Runs against MongoDB (tests/emulators.yml) when MONGODB_TEST_URI is set.
"""

from __future__ import annotations

import json
import os
import uuid

import pytest

from knowledge_store import layout
from knowledge_store.pipeline.load import load_documents
from knowledge_store.portal_api import handler, index
from knowledge_store.portal_api.docstore import DocIndex, connect
from test_review_fixes import mixed  # noqa: F401  (fixture: a collection with public and private sources)


@pytest.fixture
def db():
    uri = os.environ.get("MONGODB_TEST_URI")
    if not uri:
        pytest.skip("MONGODB_TEST_URI is not set")
    name = f"ks_test_{uuid.uuid4().hex[:8]}"
    d = connect(uri, name)
    yield d
    d.client.drop_database(name)


@pytest.fixture
def both(mixed, db, monkeypatch):
    _, lake = mixed
    ptr = load_documents(lake, db)
    index._cache.clear()
    memory = index.load(lake, "m")
    monkeypatch.setenv("PROJECTION_STORE", "mongodb")
    monkeypatch.setitem(index._db, "db", db)
    index._cache.clear()
    docs = index.load(lake, "m")
    assert isinstance(docs, DocIndex) and docs.key == ptr["key"]
    return memory, docs


QUERIES = ["", "mission", "Mission Alpha", "nova", "alph", "planet kiro", "zeta", "nothing-here"]


def test_search_and_views_match_memory(both):
    memory, docs = both
    types = [None] + [c["name"] for c in memory.ontology["classes"]]
    for private in (False, True):
        for q in QUERIES:
            for t in types:
                for offset, limit in ((0, 25), (2, 3)):
                    assert docs.search_entities(q, t, private=private, limit=limit, offset=offset) == \
                        memory.search_entities(q, t, private=private, limit=limit, offset=offset), (q, t, private)
            assert docs.search_passages(q, private=private) == memory.search_passages(q, private=private), (q, private)
        for i, e in memory.entities.items():
            assert docs.entity_view(docs.entities[i], private) == memory.entity_view(e, private)
            assert docs.graph(None, private=private, focus=i) == memory.graph(None, private=private, focus=i)
            assert docs.neighbourhood(i, hops=2, private=private) == memory.neighbourhood(i, hops=2, private=private)
            for j in memory.entities:
                assert docs.paths(i, j, private=private) == memory.paths(i, j, private=private)
        for t in types:
            for limit in (3, 150):
                assert docs.graph(t, private=private, limit=limit) == memory.graph(t, private=private, limit=limit)
        assert docs.summary_view(private) == memory.summary_view(private)
    for pid in memory.passages:
        assert docs.passage_view(pid) == memory.passage_view(pid)
    assert "nope" not in docs.entities and docs.entities.get("nope") is None


def test_portal_serves_from_the_document_store(both):
    memory, docs = both

    def call(path, qs):
        ev = {"rawPath": path, "requestContext": {"http": {"method": "GET"},
              "authorizer": {"jwt": {"claims": {"sub": "u", "cognito:groups": "[]"}}}},
              "queryStringParameters": {"c": "m", **qs}}
        return json.loads(handler.handler(ev, None)["body"])

    assert call("/api/entities", {"q": "Zeta"})["total"] == 0
    alpha = call("/api/entity", {"id": "entity/Mission/mission-alpha"})
    assert alpha["label"] == "Mission Alpha" and alpha["passage_text"]
    assert call("/api/paths", {"from": "entity/Mission/mission-alpha", "to": "entity/SpaceAgency/agency-orbis"})["hops"] == 3


def test_document_load_is_idempotent_and_rolls(mixed, db):
    from knowledge_store.store import get_json, put_json
    _, lake = mixed
    v = get_json(lake, layout.ONTOLOGY_ACTIVE)["version"]
    first = load_documents(lake, db)
    assert load_documents(lake, db) == first
    keys = [first["key"]]
    for n in (1, 2):
        summary = get_json(lake, layout.index_key(v, "summary"))
        put_json(lake, layout.index_key(v, "summary"), {**summary, "built_at": f"2030-01-0{n}T00:00:00+00:00"})
        keys.append(load_documents(lake, db)["key"])
    assert sorted(db.entities.distinct("g")) == sorted(keys[1:])
