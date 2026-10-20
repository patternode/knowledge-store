"""GraphStore offline: the load stage's rules against an in-memory store that honours the port,
the Neo4j adapter's statements against a fake driver, and choosing a backend from the environment.

The real Neo4j and AGE run the full traversal contract in test_graph.py when their emulators are up.
"""

from __future__ import annotations

import itertools
from collections import defaultdict

import pytest

from knowledge_store.knowledge_graph.adapters import backends
from knowledge_store.knowledge_graph.adapters.loading import load_graph
from knowledge_store.knowledge_graph.adapters.neo4j import Neo4jStore
from knowledge_store.knowledge_graph.domain import traverse
from knowledge_store.knowledge_graph.ports import GraphStore
from knowledge_store.platform_services.domain import layout
from knowledge_store.platform_services.ports import get_json, put_json
from test_graph import idx_of
from test_review_fixes import mixed  # noqa: F401  (fixture)


class MemoryGraphStore:
    """A GraphStore over dicts, answering the two traversal primitives from the loaded rows."""

    name = "memory"
    rendition = "neo4j/schema.cypher"

    def __init__(self):
        self.graphs: dict[str, tuple[dict, list]] = {}

    def key_for(self, collection, version, built_at):
        return f"{collection}@{version}@{built_at}"

    def load(self, key, nodes, edges, schema):
        assert schema  # the rendition was found
        self.graphs[key] = ({n["props"]["id"]: n["props"] for n in nodes}, edges)
        return {"nodes": len(nodes), "edges": len(edges)}

    def drop(self, key):
        self.graphs.pop(key, None)

    def keys(self, collection):
        return sorted(k for k in self.graphs if k.startswith(f"{collection}@"))

    def bind(self, key):
        nodes, edges = self.graphs[key]

        class Bound:
            def node(self, node_id):
                return nodes.get(node_id)

            def adjacent(self, ids, private):
                out = []
                for i in ids:
                    for e in edges:
                        for here, there in ((e["s"], e["o"]), (e["o"], e["s"])):
                            if here == i:
                                edge = {"s": e["s"], "o": e["o"], "p": e["props"]["p"], "scope": e["props"]["scope"]}
                                if private or (edge["scope"] == "public" and nodes[there]["scope"] == "public"):
                                    out.append((edge, nodes[there]))
                return out
        return Bound()


@pytest.fixture
def store() -> GraphStore:
    return MemoryGraphStore()


def test_a_loaded_graph_answers_as_the_index_does(mixed, store):  # noqa: F811
    _, lake = mixed
    ptr = load_graph(lake, store)
    memory, db = idx_of(lake), store.bind(ptr["key"])
    for private in (False, True):
        for a, b in itertools.permutations(sorted(memory.entities), 2):
            assert traverse.paths(db, a, b, max_hops=4, private=private) == memory.paths(a, b, max_hops=4, private=private)


def test_the_pointer_names_the_backend_build_and_counts(mixed, store):  # noqa: F811
    _, lake = mixed
    ptr = load_graph(lake, store)
    assert get_json(lake, layout.GRAPH_POINTER) == ptr
    assert ptr["backend"] == "memory" and ptr["previous"] is None and ptr["counts"]["nodes"] == 10


def test_a_second_load_of_the_same_build_does_nothing(mixed, store):  # noqa: F811
    _, lake = mixed
    first = load_graph(lake, store)
    store.graphs.clear()
    assert load_graph(lake, store) == first and store.graphs == {}


def test_each_new_build_keeps_one_previous_and_drops_older(mixed, store):  # noqa: F811
    _, lake = mixed
    v = get_json(lake, layout.ONTOLOGY_ACTIVE)["version"]
    keys = [load_graph(lake, store)["key"]]
    for n in (1, 2, 3):
        summary = get_json(lake, layout.index_key(v, "summary"))
        put_json(lake, layout.index_key(v, "summary"), {**summary, "built_at": f"2030-01-0{n}"})
        ptr = load_graph(lake, store)
        assert ptr["previous"] == keys[-1]
        keys.append(ptr["key"])
    assert store.keys("m") == sorted(keys[-2:])


def test_a_pointer_from_another_backend_is_not_kept_as_previous(mixed, store):  # noqa: F811
    _, lake = mixed
    put_json(lake, layout.GRAPH_POINTER, {"backend": "neo4j", "key": "other", "version": "x", "built_at": "y"})
    assert load_graph(lake, store)["previous"] is None


def test_nothing_is_loaded_without_a_projection(tmp_path, store):
    from knowledge_store.platform_services.adapters.store import LocalStore
    assert load_graph(LocalStore(tmp_path), store) is None


def test_nothing_is_loaded_when_no_backend_is_configured(mixed, monkeypatch):  # noqa: F811
    _, lake = mixed
    monkeypatch.setattr(backends, "_store", {"s": None})
    assert load_graph(lake) is None


# --- choosing a backend -------------------------------------------------------------------------


def test_no_backend_is_the_default(monkeypatch):
    monkeypatch.delenv("GRAPH_BACKEND", raising=False)
    assert backends.from_env() is None


def test_an_unknown_backend_is_refused(monkeypatch):
    monkeypatch.setenv("GRAPH_BACKEND", "oracle")
    with pytest.raises(ValueError, match="none, neo4j or age"):
        backends.from_env()


def test_the_age_backend_reads_its_settings(monkeypatch):
    monkeypatch.setenv("GRAPH_BACKEND", "age")
    monkeypatch.setenv("AGE_DSN", "host=x")
    monkeypatch.setenv("AGE_LOAD", "0")
    monkeypatch.setenv("AGE_READERS", "a, ,b")
    s = backends.from_env()
    assert (s.name, s.dsn, s.load_extension, s.readers) == ("age", "host=x", False, ["a", "b"])


def test_the_neo4j_backend_reads_its_settings(monkeypatch):
    pytest.importorskip("neo4j")
    monkeypatch.setenv("GRAPH_BACKEND", "neo4j")
    monkeypatch.setenv("NEO4J_URI", "bolt://127.0.0.1:1")
    monkeypatch.setenv("NEO4J_PASSWORD", "x")
    monkeypatch.setenv("NEO4J_DATABASE", "graphs")
    s = backends.from_env()
    assert s.name == "neo4j" and s.database == "graphs"
    s.close()


def test_the_configured_backend_is_built_once_per_process(monkeypatch):
    built = []
    monkeypatch.setattr(backends, "_store", {})
    monkeypatch.setattr(backends, "from_env", lambda: built.append(1) or "the-store")
    assert backends.store() == backends.store() == "the-store" and built == [1]


# --- the Neo4j adapter's statements ---------------------------------------------------------------


class Result:
    def __init__(self, rows):
        self.rows = rows

    def consume(self):
        return None

    def single(self):
        return self.rows[0] if self.rows else None

    def __iter__(self):
        return iter(self.rows)


class Session:
    def __init__(self, driver):
        self.driver = driver

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def run(self, text, **params):
        self.driver.ran.append((text, params))
        for needle, rows in self.driver.answers.items():
            if needle in text:
                return Result(rows)
        return Result([])


class Driver:
    def __init__(self, answers=None):
        self.ran: list[tuple[str, dict]] = []
        self.answers = answers or {}
        self.databases: list[str] = []
        self.closed = False

    def session(self, database):
        self.databases.append(database)
        return Session(self)

    def close(self):
        self.closed = True


def test_neo4j_keys_name_the_collection_version_and_build():
    s = Neo4jStore(Driver())
    k = s.key_for("m", "1.0.0", "2026-10-20T01:02:03+00:00")
    assert k.startswith("m@1.0.0@20261020010203-") and k != s.key_for("m", "1.0.0", "2026-10-21T01:02:03+00:00")


def test_neo4j_load_runs_the_schema_then_batches_nodes_by_labels_and_edges_by_type():
    d = Driver({"count(n)": [{"n": 1001}], "count(r)": [{"n": 1}]})
    nodes = [{"labels": ["Entity", "Mission"], "props": {"id": f"m{i}"}} for i in range(1001)]
    edges = [{"s": "m0", "o": "m1", "type": "LAUNCHED_BY", "props": {"p": "launchedBy"}}]
    counts = Neo4jStore(d, "db").load("g1", nodes, edges, "// a comment\nCREATE CONSTRAINT x;\n\n;")
    assert counts == {"nodes": 1001, "edges": 1}
    texts = [t for t, _ in d.ran]
    assert texts[0] == "CREATE CONSTRAINT x"
    creates = [(t, p) for t, p in d.ran if "CREATE (n:Entity:Mission)" in t]
    assert [len(p["rows"]) for _, p in creates] == [1000, 1] and all(r["g"] == "g1" for _, p in creates for r in p["rows"])
    assert any("[x:LAUNCHED_BY]" in t and p["g"] == "g1" for t, p in d.ran) and set(d.databases) == {"db"}


def test_neo4j_drop_keys_and_close():
    d = Driver({"DISTINCT n.g": [{"g": "m@2"}, {"g": "m@1"}]})
    s = Neo4jStore(d)
    s.drop("m@1")
    assert "DETACH DELETE" in d.ran[0][0] and d.ran[0][1] == {"g": "m@1"}
    assert s.keys("m") == ["m@1", "m@2"] and d.ran[-1][1] == {"p": "m@"}
    s.close()
    assert d.closed


def test_neo4j_bound_graph_answers_the_two_primitives():
    node = {"id": "a", "name": "A", "scope": "public"}
    d = Driver({"RETURN n {": [{"n": node}], "UNION ALL": [{"s": "a", "o": "b", "p": "rel", "scope": "public", "n": {"id": "b"}}]})
    bound = Neo4jStore(d).bind("g1")
    assert bound.node("a") == node
    assert bound.adjacent(["a", "a"], private=False) == [({"s": "a", "o": "b", "p": "rel", "scope": "public"}, {"id": "b"})]
    assert d.ran[-1][1] == {"ids": ["a"], "g": "g1", "private": False}


def test_neo4j_has_no_unknown_node():
    assert Neo4jStore(Driver()).bind("g1").node("nope") is None


# --- the AGE adapter's statements -----------------------------------------------------------------


class Rows(list):
    def fetchone(self):
        return self[0] if self else None

    def fetchall(self):
        return list(self)


class Conn:
    """A psycopg connection that records SQL and answers by substring."""

    closed = False

    def __init__(self, answers=None):
        self.ran: list[tuple[str, tuple]] = []
        self.answers = answers or {}

    def execute(self, sql, params=()):
        text = sql if isinstance(sql, str) else repr(sql)
        self.ran.append((text, params))
        for needle, rows in self.answers.items():
            if needle in text:
                return Rows(rows)
        return Rows()

    def close(self):
        self.closed = True


def _age(conn):
    from knowledge_store.knowledge_graph.adapters.age import AgeStore
    s = AgeStore("host=x")
    s._local.conn = conn
    return s


def test_age_keys_are_safe_graph_names_per_collection_and_build():
    s = _age(Conn())
    k = s.key_for("m", "1.0.0", "t1")
    assert k.startswith("ks_") and k == s.key_for("m", "1.0.0", "t1") != s.key_for("m", "1.0.0", "t2")
    assert k.rsplit("_", 1)[0] == s.key_for("m", "2.0.0", "t1").rsplit("_", 1)[0]


def test_age_lists_a_collections_graphs_by_its_prefix():
    c = Conn({"FROM ag_catalog.ag_graph WHERE name LIKE": [("ks_b",), ("ks_a",)]})
    s = _age(c)
    assert s.keys("m") == ["ks_a", "ks_b"] and c.ran[-1][1][0].startswith("ks_") and c.ran[-1][1][0].endswith("_%")


def test_age_drops_only_a_graph_that_exists():
    c = Conn()
    _age(c).drop("ks_gone")
    assert not any("drop_graph" in t for t, _ in c.ran)
    c = Conn({"SELECT 1 FROM ag_catalog.ag_graph": [(1,)]})
    _age(c).drop("ks_here")
    assert c.ran[-1] == ("SELECT drop_graph(%s, true)", ("ks_here",))


def test_age_bound_graph_reads_agtype_values():
    import json as _json
    from knowledge_store.knowledge_graph.adapters.age import _FIELDS
    node = ['"a"', '"A"', '"Thing"', "[]", "1", "2", '"public"'] + ["null"] * (len(_FIELDS) - 7)
    edge_row = ['"a"', '"b"', '"rel"', '"private"', '"b"', '"B"', '"Thing"', "[]", "0", "0", '"public"'] + ["null"] * (len(_FIELDS) - 7)
    c = Conn({"MATCH (n:Entity": [tuple(node)], "x.id IN $ids": [tuple(edge_row)]})
    bound = _age(c).bind("ks_g")
    n = bound.node("a")
    assert n["id"] == "a" and n["docs"] == 1 and n["scope"] == "public"
    assert "cypher('ks_g'" in c.ran[-1][0] and _json.loads(c.ran[-1][1][0]) == {"id": "a"}
    assert bound.adjacent(["a"], private=False) == []          # a private relation
    assert len(bound.adjacent(["a", "a"], private=True)) == 2  # out and in, ids once
    assert _json.loads(c.ran[-1][1][0]) == {"ids": ["a"]}


def test_age_has_no_unknown_node():
    assert _age(Conn()).bind("ks_g").node("nope") is None


def test_age_refuses_a_reader_that_is_not_a_role():
    from knowledge_store.knowledge_graph.adapters.age import AgeStore
    pytest.importorskip("psycopg")
    s = AgeStore("host=x", readers=["ghost"])
    with pytest.raises(RuntimeError, match="not a role"):
        s._grant(Conn(), "ks_g")


def test_age_closes_its_connection():
    c = Conn()
    _age(c).close()
    assert c.closed


# --- the Knowledge Base's ingestion -----------------------------------------------------------------


def test_the_knowledge_base_needs_both_ids(monkeypatch):
    from knowledge_store.knowledge_graph.adapters import loading
    monkeypatch.setenv("KNOWLEDGE_BASE_ID", "kb")
    monkeypatch.delenv("KNOWLEDGE_BASE_DATA_SOURCE_ID", raising=False)
    assert loading.knowledge_base() is None
    monkeypatch.setenv("KNOWLEDGE_BASE_DATA_SOURCE_ID", "ds")
    assert loading.knowledge_base() == ("kb", "ds")


def test_an_ingestion_job_already_running_is_left_for_the_next_sweep(monkeypatch):
    boto3 = pytest.importorskip("boto3")
    from knowledge_store.knowledge_graph.adapters import loading

    class Conflict(Exception):
        pass

    class Agent:
        exceptions = type("E", (), {"ConflictException": Conflict})

        def __init__(self, busy):
            self.busy = busy

        def start_ingestion_job(self, **kw):
            if self.busy:
                raise Conflict()
            return {"ingestionJob": {"ingestionJobId": f"job-{kw['knowledgeBaseId']}-{kw['dataSourceId']}"}}

    monkeypatch.setattr(boto3, "client", lambda name: Agent(busy=False))
    assert loading.start_ingestion(("kb", "ds")) == "job-kb-ds"
    monkeypatch.setattr(boto3, "client", lambda name: Agent(busy=True))
    assert loading.start_ingestion(("kb", "ds")) is None
