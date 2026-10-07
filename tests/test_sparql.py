"""The knowledge graph in a SPARQL store (Neptune on AWS), against rdflib's in-memory store with
Neptune's union default graph: the loader keeps the store in step with the lake, and the index
over the store gives the in-memory index's answers for every query the tools make, in both scopes.
"""

from __future__ import annotations

import itertools

import pytest

from knowledge_store import layout
from knowledge_store.graph import sparql
from knowledge_store.pipeline.load import ONTOLOGY_GRAPH, load_sparql, sync_passages
from knowledge_store.portal_api import chat, index
from knowledge_store.store import get_json, put_json
from test_graph import ALPHA, NOVA, ORBIS, ZETA
from test_review_fixes import mixed  # noqa: F401


@pytest.fixture
def loaded(mixed):
    root, lake = mixed
    client = sparql.LocalClient()
    ptr = load_sparql(lake, client)
    sparql._cache.clear()
    index._cache.clear()
    return root, lake, client, ptr


def graphs(client) -> set[str]:
    return {r["g"][1] for r in client.select("SELECT DISTINCT ?g WHERE { GRAPH ?g { ?s ?p ?o } }")}


def test_loader_holds_the_chain_and_the_tbox(loaded):
    _, lake, client, ptr = loaded
    assert ptr["counts"]["replaced"] == ptr["counts"]["graphs"] >= 4
    held = graphs(client)
    assert held == set(ptr["graphs"]) and any(g.endswith(ONTOLOGY_GRAPH) for g in held)
    # the T-Box is in the store, for queries that climb the class hierarchy
    assert client.select("SELECT ?c WHERE { ?c a <http://www.w3.org/2002/07/owl#Class> } LIMIT 1")


def test_loader_is_idempotent_and_replaces_only_what_changed(loaded):
    _, lake, client, ptr = loaded
    assert load_sparql(lake, client) == ptr                     # same build: nothing to do
    put_json(lake, layout.SPARQL_POINTER, {**ptr, "built_at": "older"})
    again = load_sparql(lake, client)
    assert again["counts"]["replaced"] == 0 and again["counts"]["dropped"] == 0


def test_loader_drops_graphs_that_left_the_chain(loaded):
    _, lake, client, ptr = loaded
    stray = ptr["graphs"] and next(g for g in ptr["graphs"] if not g.endswith(ONTOLOGY_GRAPH))
    gone = stray.rsplit("/", 1)[0] + "/not-in-the-chain"
    client.update(f"INSERT DATA {{ GRAPH <{gone}> {{ <urn:a> <urn:b> <urn:c> }} }}")
    put_json(lake, layout.SPARQL_POINTER, {**ptr, "built_at": "older"})
    assert load_sparql(lake, client)["counts"]["dropped"] == 1
    assert gone not in graphs(client)


def test_loader_reloads_a_graph_the_store_lost(loaded):
    _, lake, client, ptr = loaded
    lost = next(g for g in ptr["graphs"] if not g.endswith(ONTOLOGY_GRAPH))
    client.update(f"DROP GRAPH <{lost}>")
    put_json(lake, layout.SPARQL_POINTER, {**ptr, "built_at": "older"})
    assert load_sparql(lake, client)["counts"]["replaced"] == 1 and lost in graphs(client)


def test_index_over_the_store_answers_as_memory_does(loaded):
    _, lake, client, _ = loaded
    memory = index.load(lake, "m")
    store = sparql.load(lake, "m", client)
    ids = sorted(memory.entities)
    for private in (False, True):
        for i in ids:
            m, s = memory.entities[i], store.entities.get(i)
            assert s is not None, i
            for k in ("id", "type", "types", "label", "aliases", "passages", "docs", "scope"):
                assert s[k] == m[k], (i, k)
            for k in ("attributes", "out", "in"):
                key = (lambda r: (r["p"], r.get("v") or r.get("o") or r.get("s")))
                assert sorted(s[k], key=key) == sorted(m[k], key=key), (i, k)
            got = chat.run_tool(store, "get_entity", {"id": i}, private)
            want = chat.run_tool(memory, "get_entity", {"id": i}, private)
            assert ("error" in got) == ("error" in want), (i, private)
            for hops in (1, 2):
                assert store.neighbourhood(i, hops=hops, private=private) == \
                    memory.neighbourhood(i, hops=hops, private=private), (i, hops, private)
        for a, b in itertools.permutations(ids, 2):
            assert store.paths(a, b, max_hops=4, private=private) == memory.paths(a, b, max_hops=4, private=private)
        for q, t in (("Zeta", None), ("mission", None), ("", "Mission"), ("", None), ("nova", "SpaceAgency")):
            assert store.search_entities(q, t, private=private) == memory.search_entities(q, t, private=private), (q, t)


def test_scope_holds_in_the_store(loaded):
    _, lake, client, _ = loaded
    store = sparql.load(lake, "m", client)
    assert ZETA not in {n["id"] for n in store.neighbourhood(NOVA, private=False)["nodes"]}
    assert "error" in chat.run_tool(store, "get_entity", {"id": ZETA}, False)
    assert store.paths(ALPHA, ORBIS, private=False)["hops"] == 3


def test_types_include_subclasses_from_the_tbox(loaded):
    _, lake, client, _ = loaded
    store = sparql.load(lake, "m", client)
    parents = {c["name"]: c["parents"] for c in store.ontology["classes"]}
    child = next((c for c, ps in parents.items() if ps), None)
    if child is None:
        pytest.skip("the fixture's ontology has no subclass")
    parent = parents[child][0]
    of_child = {e["id"] for e in store.search_entities("", child, private=True, limit=100)["items"]}
    of_parent = {e["id"] for e in store.search_entities("", parent, private=True, limit=100)["items"]}
    assert of_child <= of_parent


def test_unknown_type_and_unsafe_ids_are_refused(loaded):
    _, lake, client, _ = loaded
    store = sparql.load(lake, "m", client)
    assert "error" in store.search_entities("", "NoSuchType", private=True)
    assert store.entities.get("entity/x> } DROP ALL ; { <y") is None
    assert "error" in chat.run_tool(store, "get_entity", {"id": "entity/a b"}, True)
    with pytest.raises(ValueError):
        sparql.iri("urn:a> <urn:b")
    assert sparql.lit('a"b\\c\n') == '"a\\"b\\\\c\\n"'


def test_passages_go_to_the_knowledge_base_with_scope(mixed):
    root, lake = mixed
    started = []
    ptr = sync_passages(lake, kb=("kb", "ds"), start=lambda kb: started.append(kb) or "job-1")
    assert ptr["counts"]["written"] == ptr["counts"]["passages"] > 0 and started == [("kb", "ds")]
    keys = sorted(root.list(f"{layout.KB_PASSAGES}/m/"))
    assert len(keys) == 2 * ptr["counts"]["passages"]
    metas = [get_json(root, k)["metadataAttributes"] for k in keys if k.endswith(".metadata.json")]
    assert {m["scope"] for m in metas} == {"public", "private"} and {m["collection"] for m in metas} == {"m"}
    # nothing changed: no writes, no ingestion job
    assert sync_passages(lake, kb=("kb", "ds"), start=lambda kb: started.append(kb)) == ptr and len(started) == 1
    # a job that could not start (another was running) is retried on the next sweep
    put_json(lake, layout.PASSAGES_POINTER, {**ptr, "pending": True})
    again = sync_passages(lake, kb=("kb", "ds"), start=lambda kb: None)
    assert again["pending"] is True


def test_without_a_store_or_knowledge_base_nothing_happens(mixed, monkeypatch):
    _, lake = mixed
    monkeypatch.delenv("NEPTUNE_ENDPOINT", raising=False)
    monkeypatch.delenv("KNOWLEDGE_BASE_ID", raising=False)
    assert load_sparql(lake) is None and sync_passages(lake) is None
