"""ReadModel: the projection as the tools and the portal read it, filtered by scope.

One contract, run against every implementation over the same collection (test_review_fixes'
`mixed`): the in-memory Index, the SPARQL store's index (rdflib standing in for Neptune) and the
document store's index (MongoDB, when MONGODB_TEST_URI is set). The Index's own caching and graph
binding, and the Neptune client's HTTP, are tested after the contract.
"""

from __future__ import annotations

import io
import json
import os
import urllib.error
import uuid

import pytest

from knowledge_store.knowledge_graph.adapters import index, sparql
from knowledge_store.knowledge_graph.adapters.loading import load_documents, load_sparql
from knowledge_store.knowledge_graph.ports import ReadModel
from knowledge_store.platform_services.adapters.store import LocalStore
from knowledge_store.platform_services.domain import layout
from knowledge_store.platform_services.ports import put_json
from kg_projection import ALPHA as K_ALPHA, NOVA as K_NOVA, VERSION, lake_with_projection
from test_review_fixes import mixed  # noqa: F401  (fixture)

ALPHA, NOVA = "entity/Mission/mission-alpha", "entity/SpaceAgency/agency-nova"
ZETA, ORBIS = "entity/Mission/mission-zeta", "entity/SpaceAgency/agency-orbis"


def _memory(lake):
    index._cache.clear()
    return index.load(lake, "m")


def _sparql(lake):
    client = sparql.LocalClient()
    load_sparql(lake, client)
    sparql._cache.clear()
    return sparql.load(lake, "m", client)


def _documents(lake, monkeypatch):
    uri = os.environ.get("MONGODB_TEST_URI")
    if not uri:
        pytest.skip("MONGODB_TEST_URI is not set")
    from knowledge_store.knowledge_graph.adapters.docstore import connect
    name = f"ks_test_{uuid.uuid4().hex[:8]}"
    db = connect(uri, name)
    load_documents(lake, db)
    monkeypatch.setenv("PROJECTION_STORE", "mongodb")
    monkeypatch.setitem(index._db, "db", db)
    index._cache.clear()
    return index.load(lake, "m")


@pytest.fixture(params=["memory", "sparql", "documents"])
def model(request, mixed, monkeypatch) -> ReadModel:  # noqa: F811
    _, lake = mixed
    return {"memory": lambda: _memory(lake), "sparql": lambda: _sparql(lake),
            "documents": lambda: _documents(lake, monkeypatch)}[request.param]()


def _no_text(request):
    # The SPARQL store holds no passage text, by design (ports.ReadModel); its own test is below.
    if request.node.callspec.params["model"] == "sparql":
        pytest.skip("the SPARQL store serves passages through PassageSearch")


def test_a_model_names_its_version_and_summary(model):
    assert model.version and model.summary["version"] == model.version


def test_scope_decides_what_is_visible(model):
    assert model.visible({"scope": "private"}, True) and not model.visible({"scope": "private"}, False)


def test_a_public_summary_withholds_private_counts_and_evidence(model):
    public, private = model.summary_view(False), model.summary_view(True)
    assert public["counts"] == private["public"]["counts"] and "ontology_counts" not in public
    assert all(e["scope"] == "public" for c in public["candidates"] for e in c["evidence"])
    assert all(s["scope"] == "public" for s in public["sources"])


def test_a_private_ontology_view_counts_everything(model):
    pub = {c["name"]: c["count"] for c in model.ontology_view(False)["classes"]}
    full = {c["name"]: c["count"] for c in model.ontology_view(True)["classes"]}
    assert pub["Mission"] < full["Mission"]


def test_search_entities_is_in_scope(model):
    assert model.search_entities("Zeta", private=False)["total"] == 0
    assert [i["id"] for i in model.search_entities("Zeta", private=True)["items"]] == [ZETA]


def test_search_entities_by_type(model):
    items = model.search_entities("", "SpaceAgency", private=True, limit=50)["items"]
    assert {i["id"] for i in items} >= {NOVA, ORBIS} and all(i["type"] == "SpaceAgency" for i in items)


def test_entity_view_hides_private_relations_from_a_public_caller(model):
    nova = model.search_entities("Agency Nova", private=True)["items"][0]
    assert nova["id"] == NOVA
    full = model.entity_view(model.entities[NOVA], True)
    shown = model.entity_view(model.entities[NOVA], False)
    assert ZETA in {r["s"] for r in full["in"]} and ZETA not in {r["s"] for r in shown["in"]}
    assert len(shown["passages"]) < len(full["passages"])


def test_neighbourhood_and_paths_are_in_scope(model):
    assert ZETA not in {n["id"] for n in model.neighbourhood(NOVA, private=False)["nodes"]}
    assert ZETA in {n["id"] for n in model.neighbourhood(NOVA, private=True)["nodes"]}
    assert model.paths(ALPHA, ZETA, private=False)["paths"] == []
    assert model.paths(ALPHA, ZETA, private=True)["hops"] == 2


def test_search_passages_is_in_scope(model, request):
    _no_text(request)
    public = model.search_passages("Zeta", private=False)
    private = model.search_passages("Zeta", private=True)
    assert all("Zeta" not in p["text"] for p in public) and any("Zeta" in p["text"] for p in private)


def test_passage_view_gives_the_text_and_its_document(model, request):
    _no_text(request)
    pid = next(iter(model.entity_view(model.entities[ALPHA], True)["passages"]))
    v = model.passage_view(pid)
    assert v["id"] == pid and v["doc"] and "Alpha" in v["text"]


# --- the Index's own rules ----------------------------------------------------------------------


@pytest.fixture
def small(tmp_path):
    index._cache.clear()
    return lake_with_projection(tmp_path)


def test_no_index_without_an_active_version_or_projection(tmp_path):
    index._cache.clear()
    lake = LocalStore(tmp_path)
    assert index.load(lake, "x") is None
    put_json(lake, layout.ONTOLOGY_ACTIVE, {"version": "9.9.9"})
    index._cache.clear()
    assert index.load(lake, "x") is None


def test_the_index_is_cached_until_the_build_changes(small, monkeypatch):
    first = index.load(small, "k")
    assert index.load(small, "k") is first
    monkeypatch.setattr(index, "CACHE_S", -1)
    assert index.load(small, "k") is first
    summary = json.loads(small.get(layout.index_key(VERSION, "summary")))
    put_json(small, layout.index_key(VERSION, "summary"), {**summary, "built_at": "later"})
    assert index.load(small, "k") is not first


def test_the_graph_view_shows_the_best_connected_entities_and_their_relations(small):
    idx = index.load(small, "k")
    g = idx.graph(None, private=True)
    assert {n["id"] for n in g["nodes"]} == {K_ALPHA, K_NOVA, "entity/Mission/zeta"}
    assert {(e["s"], e["o"]) for e in g["edges"]} == {(K_ALPHA, K_NOVA), ("entity/Mission/zeta", K_NOVA)}
    assert [n["id"] for n in idx.graph("Mission", private=False)["nodes"]] == [K_ALPHA]
    around = idx.graph(None, private=False, focus=K_NOVA)
    assert {n["id"] for n in around["nodes"]} == {K_NOVA, K_ALPHA}


class FakeGraphStore:
    name = "fake"

    def __init__(self):
        self.bound = []

    def bind(self, key):
        self.bound.append(key)
        return f"adjacency:{key}"


def test_traversals_use_the_graph_backend_loaded_from_this_index(small, monkeypatch):
    store = FakeGraphStore()
    monkeypatch.setattr(index.graph, "store", lambda: store)
    put_json(small, layout.GRAPH_POINTER, {"backend": "fake", "version": VERSION, "built_at": "2026-10-20T00:00:00+00:00",
                                            "key": "g1"})
    idx = index.load(small, "k")
    assert idx.adjacency == "adjacency:g1" and idx.graph_key == "g1"
    index._attach_graph(small, idx)
    assert store.bound == ["g1"]  # bound once


def test_traversals_fall_back_to_memory_when_the_graph_is_of_another_build(small, monkeypatch):
    store = FakeGraphStore()
    monkeypatch.setattr(index.graph, "store", lambda: store)
    idx = index.load(small, "k")
    idx.adjacency, idx.graph_key = "stale", "g0"
    put_json(small, layout.GRAPH_POINTER, {"backend": "fake", "version": VERSION, "built_at": "older", "key": "g0"})
    index._attach_graph(small, idx)
    assert idx.graph_key is None and idx.adjacency.idx is idx


def test_the_document_store_is_used_only_when_it_holds_this_build(small, monkeypatch):
    monkeypatch.setenv("PROJECTION_STORE", "mongodb")
    assert index._documents(small, VERSION, "x") is None  # no pointer
    put_json(small, layout.DOCUMENTS_POINTER, {"version": VERSION, "built_at": "older", "key": "d1"})
    assert index._documents(small, VERSION, "now") is None
    monkeypatch.setitem(index._db, "db", "the-db")
    put_json(small, layout.DOCUMENTS_POINTER, {"version": VERSION, "built_at": "now", "key": "d1"})
    assert index._documents(small, VERSION, "now") == ("the-db", "d1")
    monkeypatch.setenv("PROJECTION_STORE", "memory")
    assert index._documents(small, VERSION, "now") is None


def test_the_sparql_index_is_cached_and_absent_without_a_projection(mixed, tmp_path):  # noqa: F811
    _, lake = mixed
    client = sparql.LocalClient()
    load_sparql(lake, client)
    sparql._cache.clear()
    first = sparql.load(lake, "m", client)
    assert sparql.load(lake, "m", client) is first
    assert sparql.load(LocalStore(tmp_path / "empty"), "none", client) is None


# --- the Neptune client -------------------------------------------------------------------------


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_neptune_is_configured_from_the_environment(monkeypatch):
    monkeypatch.delenv("NEPTUNE_ENDPOINT", raising=False)
    assert sparql.client_from_env() is None
    monkeypatch.setenv("NEPTUNE_ENDPOINT", "db.example")
    monkeypatch.setenv("NEPTUNE_PORT", "9999")
    monkeypatch.setenv("NEPTUNE_IAM_AUTH", "false")
    c = sparql.client_from_env()
    assert c.url == "https://db.example:9999/sparql" and c.iam is False


def test_neptune_select_and_update_post_forms_and_read_bindings(monkeypatch):
    sent = []

    def urlopen(req, timeout):
        sent.append((req.full_url, req.data.decode(), dict(req.header_items())))
        body = {"results": {"bindings": [{"s": {"type": "uri", "value": "urn:a"}, "n": {"type": "literal", "value": "1"}}]}}
        return Response(json.dumps(body).encode())

    monkeypatch.setattr(sparql.urllib.request, "urlopen", urlopen)
    c = sparql.NeptuneClient("db.example", iam=False)
    assert c.select("SELECT ?s ?n WHERE {}") == [{"s": ("uri", "urn:a"), "n": ("literal", "1")}]
    c.update("CLEAR ALL")
    assert sent[0][1].startswith("query=") and sent[1][1].startswith("update=")
    assert sent[0][2]["Accept"] == "application/sparql-results+json"


def test_a_neptune_error_is_a_sparql_error(monkeypatch):
    def urlopen(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 400, "bad", {}, io.BytesIO(b"MalformedQueryException"))

    monkeypatch.setattr(sparql.urllib.request, "urlopen", urlopen)
    with pytest.raises(sparql.SparqlError, match="Neptune 400: MalformedQueryException"):
        sparql.NeptuneClient("db.example", iam=False).select("nonsense")


def test_iris_and_literals_are_escaped_and_local_names_read():
    assert sparql.iri("urn:a") == "<urn:a>" and sparql.local_name("https://x.org/o#Mission") == "Mission"
    with pytest.raises(ValueError):
        sparql.iri("")
    assert sparql.value({"a": ("uri", "x")}, "a") == "x" and sparql.value({}, "a", "d") == "d"
    assert list(sparql.chunks([1, 2, 3], 2)) == [[1, 2], [3]]


def test_the_sparql_store_leaves_passage_text_to_passage_search(mixed):  # noqa: F811
    _, lake = mixed
    model = _sparql(lake)
    with pytest.raises(NotImplementedError):
        model.search_passages("anything", private=True)
    pid = next(iter(_memory(lake).passages))
    assert "text" not in model.passage_view(pid) and model.passage_view(pid)["id"] == pid
