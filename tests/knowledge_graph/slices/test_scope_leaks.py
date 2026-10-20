"""Scope leaks closed: a public caller sees only what public documents say. Two documents that
name the same thing share one entity node, so its names, types and counts are kept per scope; the
summary's candidates, sources and counts and the ontology's counts are public-only for a public
caller; a metric over a private table is hidden as describe_structured hides it."""

from __future__ import annotations

import json

import pytest
from rdflib import Dataset

from knowledge_store.platform_services.domain import layout
from knowledge_store.platform_services.slices.config import SourceConfig
from knowledge_store.knowledge_graph.adapters import sparql
from knowledge_store.knowledge_graph.domain import traverse
from knowledge_store.ontology.slices import versions
from knowledge_store.knowledge_graph.slices import project
from knowledge_store.ingestion.adapters.registry import ingest_source
from knowledge_store.knowledge_graph.adapters.loading import load_sparql
from knowledge_store.ingestion.slices.refine import load_doc
from knowledge_store.answering.adapters import fallback_chat as chat
from knowledge_store.knowledge_graph.adapters import index
from knowledge_store.knowledge_graph.adapters.index import Index
from knowledge_store.platform_services.ports import put_json
from knowledge_store.extraction.slices.bind_tables import bind
from knowledge_store.knowledge_graph.slices.table_query import aggregate, describe
from test_graph import ALPHA, NOVA, ZETA
from test_review_fixes import _call, mixed  # noqa: F401  (fixture: a collection with public and private sources)
from test_structured import CORPUS, _collection, _copy, _edit

SECRET_ALIAS, PUBLIC_ALIAS, SECRET_LABEL = "Codename Nightjar", "Nova Space", "AGENCY NOVA (classified)"
SECRETS = ("Hush device", "SECRETDEF", "What does Hush detect?", "SecretThing")


def _add(lake, scope: str, lines) -> None:
    """Add triples about Agency Nova to the graph of a document of this scope that mentions it."""
    for v in versions.chain(lake, versions.active_version(lake)):
        for key in lake.list(f"{layout.gold_prefix(v)}/graph/"):
            if not key.endswith(".nq") or load_doc(lake, layout.doc_id_from_key(key)).get("scope", "public") != scope:
                continue
            text = lake.get(key).decode()
            if "agency-nova" not in text:
                continue
            ds = Dataset()
            ds.parse(data=text, format="nquads")
            g = next(c.identifier for c in ds.graphs() if len(c))
            iri = next(str(s) for s, *_ in ds.quads((None, None, None, None)) if str(s).endswith(NOVA))
            extra = "".join(f"<{iri}> <{p}> {o} <{g}> .\n" for p, o in lines)
            lake.put(key, (text.rstrip("\n") + "\n" + extra).encode())
            return
    raise AssertionError(f"no {scope} graph mentions Agency Nova")


@pytest.fixture
def shared(mixed):  # noqa: F811
    """The mixed collection, with names and a type for Agency Nova stated only by its private
    document, a name stated by a public one, and a register entry carrying curator requests."""
    root, lake = mixed
    ns = json.loads(lake.get(layout.index_key(versions.active_version(lake), "ontology")))["namespace"]
    alt, label = "http://www.w3.org/2004/02/skos/core#altLabel", "http://www.w3.org/2000/01/rdf-schema#label"
    _add(lake, "private", [(alt, f'"{SECRET_ALIAS}"'), (label, f'"{SECRET_LABEL}"'),
                           ("http://www.w3.org/1999/02/22-rdf-syntax-ns#type", f"<{ns}TargetBody>")])
    _add(lake, "public", [(alt, f'"{PUBLIC_ALIAS}"')])
    reg = json.loads(lake.get(layout.CANDIDATE_REGISTER))
    t = next(t for t in reg["terms"] if t["term"] == "Instrument")
    t.update(also=[*t["also"], SECRETS[0]], definitions=[*t["definitions"], SECRETS[1]], questions=[SECRETS[2]],
             asked=1, nearest=SECRETS[3])
    put_json(lake, layout.CANDIDATE_REGISTER, reg)
    project.project(lake)
    index._cache.clear()
    return root, lake


def test_names_and_types_from_a_private_document_are_not_shown(shared):
    _, pub = _call("/api/entity", private=False, qs={"id": NOVA})
    _, priv = _call("/api/entity", private=True, qs={"id": NOVA})
    assert pub["label"] == priv["label"] == "Agency Nova"
    assert pub["aliases"] == [PUBLIC_ALIAS] and set(priv["aliases"]) == {PUBLIC_ALIAS, SECRET_ALIAS}
    assert "TargetBody" not in pub["types"] and "TargetBody" in priv["types"]
    assert SECRET_ALIAS not in json.dumps(pub) and SECRET_LABEL not in json.dumps(pub) and "public" not in pub
    assert len(pub["docs"]) < len(priv["docs"])


def test_search_matches_public_names_only(shared):
    for q in (SECRET_ALIAS, "nightjar", "classified"):
        assert _call("/api/entities", private=False, qs={"q": q})[1]["total"] == 0, q
    assert _call("/api/entities", private=True, qs={"q": "nightjar"})[1]["items"][0]["id"] == NOVA
    found = _call("/api/entities", private=False, qs={"q": "nova space"})[1]["items"]
    assert found[0]["id"] == NOVA and found[0]["aliases"] == [PUBLIC_ALIAS]
    # a type only a private document gives it does not find it for a public caller
    assert NOVA not in {i["id"] for i in _call("/api/entities", private=False, qs={"type": "TargetBody"})[1]["items"]}
    assert NOVA in {i["id"] for i in _call("/api/entities", private=True, qs={"type": "TargetBody"})[1]["items"]}
    # the brief's counts are of public documents and relations
    lst = {i["id"]: i for i in _call("/api/entities", private=False, qs={"q": "agency nova"})[1]["items"]}
    full = {i["id"]: i for i in _call("/api/entities", private=True, qs={"q": "agency nova"})[1]["items"]}
    assert lst[NOVA]["docs"] < full[NOVA]["docs"] and lst[NOVA]["links"] < full[NOVA]["links"]


def test_traversals_show_public_names_only(shared):
    _, lake = shared
    idx = index.load(lake, "m")
    for out in (idx.neighbourhood(ALPHA, private=False), idx.paths(ALPHA, NOVA, private=False)["paths"][0],
                idx.graph(None, private=False, focus=NOVA)):
        nova = next(n for n in out["nodes"] if n["id"] == NOVA)
        assert nova["aliases"] == [PUBLIC_ALIAS] and nova["type"] == "SpaceAgency"
    nova = next(n for n in idx.neighbourhood(ALPHA, private=True)["nodes"] if n["id"] == NOVA)
    assert SECRET_ALIAS in nova["aliases"]


def test_the_graph_store_keeps_names_per_scope(shared):
    _, lake = shared
    client = sparql.LocalClient()
    load_sparql(lake, client)
    sparql._cache.clear()
    store, memory = sparql.load(lake, "m", client), index.load(lake, "m")
    e = store.entities.get(NOVA)
    assert e["label"] == "Agency Nova" and e["public"]["aliases"] == [PUBLIC_ALIAS] and "TargetBody" not in e["public"]["types"]
    assert SECRET_ALIAS in e["aliases"]
    assert store.search_entities("nightjar", private=False)["total"] == 0
    assert store.search_entities("nightjar", private=True)["total"] == 1
    assert NOVA not in {i["id"] for i in store.search_entities("", "TargetBody", private=False)["items"]}
    assert NOVA in {i["id"] for i in store.search_entities("", "TargetBody", private=True)["items"]}
    for private in (False, True):
        assert store.search_entities("nova", private=private) == memory.search_entities("nova", private=private)
        assert store.neighbourhood(NOVA, private=private) == memory.neighbourhood(NOVA, private=private)
        got, want = (chat.run_tool(x, "get_entity", {"id": NOVA}, private) for x in (store, memory))
        assert (got["aliases"], got["types"], got["type"]) == (want["aliases"], want["types"], want["type"])


def test_summary_shows_public_fields_only(shared):
    _, pub = _call("/api/summary", private=False)
    _, priv = _call("/api/summary", private=True)
    text = json.dumps(pub)
    for s in SECRETS:
        assert s not in text, s
        assert s in json.dumps(priv["candidates"]), s
    assert all(not ({"questions", "asked", "nearest"} & set(t)) for t in pub["candidates"])
    inst = next(t for t in pub["candidates"] if t["term"] == "Instrument")
    assert inst["evidence"] and all(e["scope"] == "public" for e in inst["evidence"])
    assert [s["name"] for s in pub["sources"]] == ["public"] and {s["name"] for s in priv["sources"]} == {"public", "private"}
    assert all(set(h) <= set(index.PUBLIC_HISTORY) for h in pub["history"])
    assert "ontology_counts" not in pub and "public" not in pub
    assert pub["counts"]["entities"] < priv["counts"]["entities"]
    assert "silver_documents" not in pub["counts"]


def test_ontology_counts_are_public_for_a_public_caller(shared):
    _, lake = shared
    idx = index.load(lake, "m")
    pub, priv = idx.ontology_view(False), idx.ontology_view(True)
    assert pub is idx.ontology  # what /api/ontology serves to everyone
    count = lambda o, n: next(c["count"] for c in o["classes"] if c["name"] == n)  # noqa: E731
    assert count(pub, "Mission") == count(priv, "Mission") - 1      # Mission Zeta is private
    assert count(pub, "TargetBody") < count(priv, "TargetBody")      # a type only the private document gives
    seen = lambda o: {(x["domain"], x["p"], x["range"]): x["count"] for x in o["observed"]}  # noqa: E731
    key = ("Mission", "launchedBy", "SpaceAgency")
    assert seen(pub)[key] == seen(priv)[key] - 1


def _index(entities, passages, docs) -> Index:
    idx = object.__new__(Index)
    idx.entities, idx.passages, idx.docs = {e["id"]: e for e in entities}, passages, docs
    idx.by_type = {}
    for e in entities:
        for t in e["types"]:
            idx.by_type.setdefault(t, []).append(e["id"])
    idx.adjacency = traverse.MemoryAdjacency(idx)
    return idx


def test_a_fact_shows_only_its_public_passages_and_old_data_fails_closed():
    docs = {"d1": {"scope": "public"}, "d2": {"scope": "private"}}
    passages = {"p1": {"doc": "d1", "scope": "public"}, "p2": {"doc": "d2", "scope": "private"}}
    e = {"id": "entity/A/a", "type": "A", "types": ["A", "B"], "label": "A", "aliases": ["secret name"],
         "attributes": [{"p": "x", "v": "1", "passages": ["p1", "p2"]}, {"p": "y", "v": "2", "passages": ["p2"]},
                        {"p": "z", "v": "3", "passages": ["unknown"]}],
         "out": [], "in": [], "passages": ["p1", "p2"], "docs": ["d1", "d2", "gone"], "scope": "public"}  # no `public`
    idx = _index([e], passages, docs)
    v = idx.entity_view(e, False)
    assert v["attributes"] == [{"p": "x", "v": "1", "passages": ["p1"]}]
    assert v["passages"] == ["p1"] and v["docs"] == ["d1"]
    assert v["aliases"] == [] and v["types"] == ["A"]
    assert idx.search_entities("secret", private=False)["total"] == 0
    assert idx.search_entities("secret", private=True)["total"] == 1
    assert idx.search_entities("", "B", private=False)["total"] == 0
    assert idx.entity_view(e, True)["attributes"] == e["attributes"]
    assert idx.search_entities("a" * 5000, private=True)["total"] == 0  # a long query is cut, not scanned whole


def test_a_metric_over_a_private_table_is_hidden(tmp_path):
    root, lake = _collection(tmp_path)
    dest = _copy(tmp_path)
    _edit(dest / "mappings.yaml", "class: Mission\n    key:", "class: Mission\n    scope: private\n    key:")
    versions.publish(lake, dest, activate=True)
    ingest_source(lake, SourceConfig("missions-tables", "local_dir", {"path": str(CORPUS), "pattern": "tables/*.csv"}))
    bind(lake)
    assert "atlas_v_launches" not in {m["name"] for m in describe(lake)["metrics"]}
    hidden = aggregate(lake, metric="atlas_v_launches")
    assert "error" in hidden and "description" not in hidden
    assert "error" in aggregate(lake, type_name="Mission", op="count")
    shown = aggregate(lake, metric="atlas_v_launches", private=True)
    assert "error" not in shown and shown["figure"]


# -- graph stores (Neo4j, AGE) keep the public view flat -------------------------------------

def test_graph_rows_carry_the_public_view_and_brief_reads_it():
    from types import SimpleNamespace as NS
    from knowledge_store.knowledge_graph.domain.graph_rows import rows
    from knowledge_store.knowledge_graph.domain import traverse
    spec = NS(classes={}, ancestors=lambda t: [t])
    e = {"id": "entity/org/nova", "label": "Agency Nova", "type": "SecretUnit", "types": ["Organisation", "SecretUnit"],
         "aliases": ["BLACKBIRD", "Nova"], "scope": "public", "docs": ["d1", "d2"], "out": [], "in": [],
         "passages": [], "attributes": [],
         "public": {"type": "Organisation", "types": ["Organisation"], "aliases": ["Nova"], "docs": 1, "links": 0}}
    nodes, _ = rows([e], {}, spec, "https://x/")
    n = nodes[0]["props"]
    assert n["public_type"] == "Organisation" and n["public_aliases"] == ["Nova"]
    seen = traverse.brief({k: n.get(k) for k in ("id", "name", "type", "aliases", "docs", "links", "scope",
                                                  "public_type", "public_types", "public_aliases",
                                                  "public_docs", "public_links")}, private=False)
    assert seen["type"] == "Organisation" and seen["aliases"] == ["Nova"] and seen["docs"] == 1
    assert "BLACKBIRD" in traverse.brief({**n, "name": n["name"]}, private=True)["aliases"]


def test_a_graph_store_node_loaded_before_the_public_view_shows_no_aliases():
    from knowledge_store.knowledge_graph.domain import traverse
    old = {"id": "x", "name": "X", "type": "Organisation", "aliases": ["BLACKBIRD"], "docs": 3, "links": 2,
           "scope": "public", "public_type": None, "public_types": None, "public_aliases": None}
    seen = traverse.brief(old, private=False)
    assert seen["aliases"] == [] and seen["docs"] == 0


def test_the_graph_stores_return_the_public_fields():
    from knowledge_store.knowledge_graph.adapters import age
    from knowledge_store.knowledge_graph.adapters import neo4j
    for f in ("public_type", "public_types", "public_aliases", "public_docs", "public_links"):
        assert f".{f}" in neo4j._BRIEF and f in age._FIELDS and f"y.{f}" in age._returned("y")
