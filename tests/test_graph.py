"""The graph projection: renditions, the load stage, and one traversal contract for memory, Neo4j
and AGE. The backends are loaded from the same projection and must give the in-memory index's
answers for every neighbourhood and every pair of entities, for both scopes.

Neo4j and AGE run against the containers in tests/emulators.yml when NEO4J_TEST_URI or
AGE_TEST_DSN is set, and are skipped otherwise.
"""

from __future__ import annotations

import itertools
import json
import os

import pytest

from knowledge_store import graph, layout
from knowledge_store.graph import traverse
from knowledge_store.pipeline.load import load_graph
from knowledge_store.portal_api import index
from knowledge_store.store import get_json, put_json
from test_review_fixes import mixed  # noqa: F401  (fixture: a collection with public and private sources)

ALPHA, ORBIS = "entity/Mission/mission-alpha", "entity/SpaceAgency/agency-orbis"
NOVA, ZETA = "entity/SpaceAgency/agency-nova", "entity/Mission/mission-zeta"


def idx_of(lake):
    index._cache.clear()
    return index.load(lake, "m")


# --- renditions ---------------------------------------------------------------------------


def test_release_renders_graph_schemas(mixed):
    _, lake = mixed
    v = get_json(lake, layout.ONTOLOGY_ACTIVE)["version"]
    pre = f"{layout.ontology_version_prefix(v)}/renditions"
    age = lake.get(f"{pre}/age/schema.sql").decode()
    assert "SELECT create_elabel('{graph}', 'LAUNCHED_BY');" in age
    assert "REQUIRE (n.g, n.id) IS UNIQUE" in lake.get(f"{pre}/neo4j/schema.cypher").decode()
    mapping = json.loads(lake.get(f"{pre}/neo4j/mapping.json"))
    assert mapping["node_key"] == "id" and mapping["graph_key"] == "g"


def test_rows_follow_the_mapping(mixed):
    _, lake = mixed
    from knowledge_store.extract.rdf import data_base
    from knowledge_store.ontology import versions
    v = versions.active_version(lake)
    spec, _ = versions.load_version(lake, v)
    nodes, edges = graph.rows(get_json(lake, layout.index_key(v, "entities")),
                              get_json(lake, layout.index_key(v, "passages")), spec, data_base(spec))
    zeta = next(n for n in nodes if n["props"]["id"] == ZETA)
    assert zeta["labels"][:2] == ["Entity", "Mission"] and zeta["props"]["scope"] == "private"
    assert zeta["props"]["iri"].endswith(ZETA)
    from_zeta = [e for e in edges if e["s"] == ZETA]
    assert from_zeta and all(e["props"]["scope"] == "private" and e["type"] == "LAUNCHED_BY" for e in from_zeta)
    with pytest.raises(ValueError):
        graph.safe_name("Bad Label) DETACH DELETE n //")


# --- the traversal contract -----------------------------------------------------------------


def test_scope_is_enforced_along_the_way(mixed):
    _, lake = mixed
    idx = idx_of(lake)
    public = {n["id"] for n in idx.neighbourhood(NOVA, hops=1, private=False)["nodes"]}
    private = {n["id"] for n in idx.neighbourhood(NOVA, hops=1, private=True)["nodes"]}
    assert ZETA not in public and ZETA in private
    assert idx.neighbourhood(ZETA, private=False)["nodes"] == []
    assert idx.paths(ALPHA, ZETA, private=False)["paths"] == []
    assert idx.paths(ALPHA, ZETA, private=True)["hops"] == 2


def test_shortest_paths(mixed):
    _, lake = mixed
    out = idx_of(lake).paths(ALPHA, ORBIS, max_hops=4, private=False)
    assert out["hops"] == 3
    assert [[n["id"] for n in p["nodes"]] for p in out["paths"]] == \
        [[ALPHA, "entity/TargetBody/planet-kiro", "entity/Mission/mission-delta", ORBIS]]
    assert out["paths"][0]["edges"][0] == {"s": ALPHA, "o": "entity/TargetBody/planet-kiro", "p": "studies"}
    assert idx_of(lake).paths(ALPHA, ORBIS, max_hops=2, private=False)["paths"] == []


@pytest.fixture(params=["neo4j", "age"])
def backend(request):
    if request.param == "neo4j":
        uri = os.environ.get("NEO4J_TEST_URI")
        if not uri:
            pytest.skip("NEO4J_TEST_URI is not set")
        from neo4j import GraphDatabase
        from knowledge_store.graph.neo4j import Neo4jStore
        s = Neo4jStore(GraphDatabase.driver(uri, auth=("neo4j", os.environ["NEO4J_TEST_PASSWORD"])))
    else:
        dsn = os.environ.get("AGE_TEST_DSN")
        if not dsn:
            pytest.skip("AGE_TEST_DSN is not set")
        import psycopg
        from knowledge_store.graph.age import AgeStore
        with psycopg.connect(dsn, autocommit=True) as c:
            c.execute("CREATE EXTENSION IF NOT EXISTS age")
        s = AgeStore(dsn)
    for k in s.keys("m"):
        s.drop(k)
    yield s
    for k in s.keys("m"):
        s.drop(k)
    s.close()


def test_backend_answers_as_memory_does(mixed, backend, monkeypatch):
    _, lake = mixed
    ptr = load_graph(lake, backend)
    assert ptr["counts"]["nodes"] == 10 and ptr["counts"]["edges"] > 0
    memory = idx_of(lake)
    db = backend.bind(ptr["key"])
    ids = sorted(memory.entities)
    for private in (False, True):
        for i in ids:
            for hops in (1, 2):
                assert traverse.neighbourhood(db, i, hops=hops, private=private) == \
                    memory.neighbourhood(i, hops=hops, private=private), (i, hops, private)
        for a, b in itertools.permutations(ids, 2):
            assert traverse.paths(db, a, b, max_hops=4, private=private) == \
                memory.paths(a, b, max_hops=4, private=private), (a, b, private)
    # the portal switches to the backend only for the index the graph was loaded from
    monkeypatch.setitem(graph._store, "s", backend)
    idx = idx_of(lake)
    assert idx.graph_key == ptr["key"]
    assert idx.paths(ALPHA, ORBIS, private=False)["hops"] == 3


def test_load_is_idempotent_keeps_one_previous_and_drops_older(mixed, backend):
    _, lake = mixed
    v = get_json(lake, layout.ONTOLOGY_ACTIVE)["version"]
    first = load_graph(lake, backend)
    assert load_graph(lake, backend) == first  # nothing changed, nothing loaded
    keys = [first["key"]]
    for n in (1, 2):
        summary = get_json(lake, layout.index_key(v, "summary"))
        put_json(lake, layout.index_key(v, "summary"), {**summary, "built_at": f"2030-01-0{n}T00:00:00+00:00"})
        ptr = load_graph(lake, backend)
        assert ptr["previous"] == keys[-1]
        keys.append(ptr["key"])
    assert backend.keys("m") == sorted(keys[1:])


def test_a_load_that_miscounts_is_dropped_and_not_pointed_at(mixed):
    _, lake = mixed

    class Short:
        name, rendition = "fake", "neo4j/schema.cypher"
        dropped: list = []

        def key_for(self, *a):
            return "k"

        def drop(self, key):
            self.dropped.append(key)

        def load(self, key, nodes, edges, schema):
            return {"nodes": len(nodes) - 1, "edges": len(edges)}

        def keys(self, c):
            return []

    s = Short()
    with pytest.raises(RuntimeError):
        load_graph(lake, s)
    assert s.dropped == ["k", "k"] and not lake.exists(layout.GRAPH_POINTER)
    assert idx_of(lake).paths(ALPHA, ORBIS, private=False)["hops"] == 3  # memory still answers


def test_age_readers_can_read_but_not_write(mixed):
    dsn = os.environ.get("AGE_TEST_DSN")
    if not dsn:
        pytest.skip("AGE_TEST_DSN is not set")
    import psycopg
    from knowledge_store.graph.age import AgeStore
    with psycopg.connect(dsn, autocommit=True) as c:
        if not c.execute("SELECT 1 FROM pg_roles WHERE rolname = 'ks_reader'").fetchone():
            c.execute("CREATE ROLE ks_reader LOGIN PASSWORD 'reader-test'")
    writer = AgeStore(dsn, readers=["ks_reader"])
    for k in writer.keys("m"):
        writer.drop(k)
    _, lake = mixed
    ptr = load_graph(lake, writer)
    reader_dsn = " ".join(p for p in dsn.split() if not p.startswith(("user=", "password="))) + " user=ks_reader password=reader-test"
    reader = AgeStore(reader_dsn, load_extension=False)
    assert traverse.paths(reader.bind(ptr["key"]), ALPHA, ORBIS, private=False)["hops"] == 3
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        reader._conn().execute(f'DELETE FROM "{ptr["key"]}"."Entity"')
    reader.close()
    for k in writer.keys("m"):
        writer.drop(k)
    writer.close()
