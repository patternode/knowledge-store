"""SparqlStore: select and update over the gold graphs, with the default graph the union of the
named graphs (as Neptune's is). rdflib runs offline; a real Neptune runs when NEPTUNE_TEST_ENDPOINT
is set (with NEPTUNE_IAM_AUTH as the cluster needs)."""

from __future__ import annotations

import os
import uuid

import pytest

from knowledge_store.knowledge_graph.adapters import sparql
from knowledge_store.knowledge_graph.ports import SparqlStore


@pytest.fixture(params=["local", "neptune"])
def store(request) -> SparqlStore:
    if request.param == "local":
        return sparql.LocalClient()
    host = os.environ.get("NEPTUNE_TEST_ENDPOINT")
    if not host:
        pytest.skip("NEPTUNE_TEST_ENDPOINT is not set")
    return sparql.NeptuneClient(host, iam=os.environ.get("NEPTUNE_IAM_AUTH", "true") != "false")


@pytest.fixture
def graph(store):
    g = f"urn:test:{uuid.uuid4().hex}"
    store.update(f'INSERT DATA {{ GRAPH <{g}> {{ <urn:a> <urn:p> <urn:b> . <urn:a> <urn:label> "Alpha" . }} }}')
    yield g
    store.update(f"DROP SILENT GRAPH <{g}>")


def test_a_select_returns_each_binding_with_its_kind(store, graph):
    rows = store.select(f"SELECT ?o WHERE {{ GRAPH <{graph}> {{ <urn:a> ?p ?o }} }} ORDER BY ?o")
    assert sorted(r["o"] for r in rows) == [("literal", "Alpha"), ("uri", "urn:b")]


def test_the_default_graph_is_the_union_of_the_named_graphs(store, graph):
    assert store.select('SELECT ?s WHERE { ?s <urn:label> "Alpha" }') == [{"s": ("uri", "urn:a")}]


def test_an_unbound_variable_is_left_out(store, graph):
    rows = store.select(f"SELECT ?s ?missing WHERE {{ GRAPH <{graph}> {{ ?s <urn:p> ?o }} OPTIONAL {{ ?s <urn:none> ?missing }} }}")
    assert rows == [{"s": ("uri", "urn:a")}]


def test_an_update_removes_what_it_deletes(store, graph):
    store.update(f"DROP GRAPH <{graph}>")
    assert store.select(f"SELECT ?s WHERE {{ GRAPH <{graph}> {{ ?s ?p ?o }} }}") == []


def test_a_blank_node_is_reported_as_one(store, graph):
    store.update(f"INSERT DATA {{ GRAPH <{graph}> {{ _:x <urn:p> <urn:c> }} }}")
    kinds = {r["s"][0] for r in store.select(f"SELECT ?s WHERE {{ GRAPH <{graph}> {{ ?s <urn:p> ?o }} }}")}
    assert kinds == {"uri", "bnode"}
