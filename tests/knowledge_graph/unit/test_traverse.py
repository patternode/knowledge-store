"""Neighbourhoods and paths over the Adjacency primitives, with scope enforced along the way.

The graph is a small dict-backed Adjacency, so every rule is shown without a lake or a backend:

    A --rel--> B --rel--> C          all public
    A --rel--> P --rel--> C          P is a private entity
    B --secret--> D                  a private relation to a public entity
    A --self--> A                    a loop, never a step
"""

from __future__ import annotations

import pytest

from knowledge_store.knowledge_graph.domain import traverse


def node(i, scope="public", links=1, **extra):
    return {"id": i, "name": i.upper(), "type": "Thing", "aliases": [f"{i}-alias"], "docs": 2, "links": links,
            "scope": scope, **extra}


class Graph:
    """An Adjacency over a list of edges; it returns what it holds and lets traverse filter."""

    def __init__(self, nodes, edges):
        self.nodes = {n["id"]: n for n in nodes}
        self.edges = edges
        self.calls: list[list[str]] = []

    def node(self, node_id):
        return self.nodes.get(node_id)

    def adjacent(self, ids, private):
        self.calls.append(list(ids))
        out = []
        for i in ids:
            for e in self.edges:
                if e["s"] == i:
                    out.append((e, self.nodes[e["o"]]))
                if e["o"] == i:
                    out.append((e, self.nodes[e["s"]]))
        return out


def edge(s, o, p="rel", scope="public"):
    return {"s": s, "o": o, "p": p, "scope": scope}


@pytest.fixture
def g():
    return Graph([node("a", links=3), node("b", links=3), node("c", links=2), node("p", "private"), node("d")],
                 [edge("a", "b"), edge("b", "c"), edge("a", "p"), edge("p", "c"),
                  edge("b", "d", "secret", "private"), edge("a", "a", "self")])


# --- visible and public_names --------------------------------------------------------------


def test_a_private_caller_sees_everything():
    assert traverse.visible({"scope": "private"}, True)


def test_a_public_caller_sees_only_public_items():
    assert not traverse.visible({"scope": "private"}, False)
    assert traverse.visible({"scope": "public"}, False)


def test_an_item_without_a_scope_is_public():
    assert traverse.visible({}, False)


def test_public_names_come_from_the_projections_public_record():
    e = {"type": "Mission", "public": {"type": "Probe", "types": ["Probe", "Mission"], "aliases": ["P1"], "docs": 2, "links": 1}}
    assert traverse.public_names(e) == {"aliases": ["P1"], "types": ["Probe", "Mission"], "type": "Probe", "docs": 2,
                                        "links": 1}


def test_public_names_read_a_graph_stores_flat_form():
    e = {"type": "Mission", "public_type": "Probe", "public_types": ["Probe"], "public_aliases": ["P1"],
         "public_docs": 3, "public_links": 4}
    assert traverse.public_names(e) == {"aliases": ["P1"], "types": ["Probe"], "type": "Probe", "docs": 3, "links": 4}


def test_without_public_provenance_no_aliases_or_counts_are_shown():
    assert traverse.public_names({"type": "Mission"}) == {"aliases": [], "types": ["Mission"], "type": "Mission",
                                                          "docs": 0, "links": 0}


def test_public_types_without_a_type_take_the_first_type():
    assert traverse.public_names({"type": "X", "public": {"types": ["Probe", "Mission"]}})["type"] == "Probe"


def test_brief_shows_a_private_caller_the_full_record():
    b = traverse.brief(node("a", aliases=list("abcdefg")), private=True)
    assert b == {"id": "a", "label": "A", "type": "Thing", "aliases": list("abcde"), "docs": 2, "links": 1}


def test_brief_shows_a_public_caller_only_public_names():
    b = traverse.brief(node("a"), private=False)
    assert b["aliases"] == [] and b["docs"] == 0 and b["links"] == 0


# --- neighbourhood --------------------------------------------------------------------------


def test_a_neighbourhood_starts_with_its_focus(g):
    out = traverse.neighbourhood(g, "a", private=True)
    assert out["nodes"][0]["id"] == "a" and out["hops"] == 1


def test_one_hop_reaches_direct_neighbours_only(g):
    ids = {n["id"] for n in traverse.neighbourhood(g, "a", hops=1, private=True)["nodes"]}
    assert ids == {"a", "b", "p"}


def test_two_hops_reach_neighbours_of_neighbours(g):
    ids = {n["id"] for n in traverse.neighbourhood(g, "a", hops=2, private=True)["nodes"]}
    assert ids == {"a", "b", "p", "c", "d"}


def test_a_public_caller_never_passes_through_a_private_entity_or_relation(g):
    ids = {n["id"] for n in traverse.neighbourhood(g, "a", hops=2, private=False)["nodes"]}
    assert ids == {"a", "b", "c"}


def test_a_private_focus_is_empty_to_a_public_caller(g):
    assert traverse.neighbourhood(g, "p", private=False) == {"nodes": [], "edges": [], "hops": 1}


def test_an_unknown_focus_is_empty(g):
    assert traverse.neighbourhood(g, "nope", private=True)["nodes"] == []


def test_hops_are_clamped_to_the_maximum(g):
    assert traverse.neighbourhood(g, "a", hops=99, private=True)["hops"] == traverse.MAX_NEIGHBOURHOOD_HOPS
    assert traverse.neighbourhood(g, "a", hops=0, private=True)["hops"] == 1


def test_the_limit_caps_the_nodes_nearest_first(g):
    out = traverse.neighbourhood(g, "a", hops=2, private=True, limit=2)
    assert [n["id"] for n in out["nodes"]][0] == "a" and len(out["nodes"]) == 2


def test_nearer_nodes_come_before_farther_ones_then_the_best_connected(g):
    ids = [n["id"] for n in traverse.neighbourhood(g, "a", hops=2, private=True)["nodes"]]
    assert ids.index("b") < ids.index("c") and ids.index("b") < ids.index("p")


def test_edges_are_only_among_kept_nodes_and_never_loops(g):
    out = traverse.neighbourhood(g, "a", hops=1, private=True)
    kept = {n["id"] for n in out["nodes"]}
    assert out["edges"] and all(e["s"] in kept and e["o"] in kept and e["s"] != e["o"] for e in out["edges"])


def test_the_walk_reads_one_layer_per_call(g):
    traverse.neighbourhood(g, "a", hops=2, private=True)
    assert g.calls[0] == ["a"]


# --- paths ---------------------------------------------------------------------------------


def test_every_shortest_path_is_found(g):
    out = traverse.paths(g, "a", "c", private=True)
    assert out["hops"] == 2 and not out["truncated"]
    assert sorted(tuple(n["id"] for n in p["nodes"]) for p in out["paths"]) == [("a", "b", "c"), ("a", "p", "c")]


def test_a_path_keeps_each_relations_own_direction(g):
    out = traverse.paths(g, "c", "a", private=True)
    first = out["paths"][0]
    assert first["edges"][-1] in ({"s": "a", "o": "b", "p": "rel"}, {"s": "a", "o": "p", "p": "rel"})


def test_a_public_caller_finds_only_public_paths(g):
    out = traverse.paths(g, "a", "c", private=False)
    assert [[n["id"] for n in p["nodes"]] for p in out["paths"]] == [["a", "b", "c"]]


def test_a_target_reachable_only_through_private_text_is_unreachable_in_public(g):
    assert traverse.paths(g, "a", "d", private=False)["paths"] == []
    assert traverse.paths(g, "a", "d", private=True)["hops"] == 2


def test_a_path_to_itself_is_empty(g):
    assert traverse.paths(g, "a", "a", private=True) == {"paths": [], "hops": None, "truncated": False}


def test_a_path_from_or_to_an_unknown_entity_is_empty(g):
    assert traverse.paths(g, "a", "nope", private=True)["paths"] == []
    assert traverse.paths(g, "nope", "a", private=True)["paths"] == []


def test_a_path_to_a_private_entity_is_empty_in_public(g):
    assert traverse.paths(g, "a", "p", private=False)["paths"] == []


def test_a_target_beyond_max_hops_is_not_found(g):
    assert traverse.paths(g, "a", "c", max_hops=1, private=True)["paths"] == []


def test_the_limit_caps_the_paths_returned(g):
    assert len(traverse.paths(g, "a", "c", private=True, limit=1)["paths"]) == 1


def test_a_disconnected_target_stops_when_the_frontier_is_empty():
    lone = Graph([node("a"), node("z")], [])
    assert traverse.paths(lone, "a", "z", private=True) == {"paths": [], "hops": None, "truncated": False}


def test_a_search_that_visits_too_much_is_marked_truncated(monkeypatch):
    star = Graph([node("hub"), node("t"), *[node(f"n{i}") for i in range(5)]], [edge("hub", f"n{i}") for i in range(5)])
    monkeypatch.setattr(traverse, "MAX_VISITED", 2)
    assert traverse.paths(star, "hub", "t", private=True) == {"paths": [], "hops": None, "truncated": True}


def test_too_many_shortest_paths_are_capped_and_marked_truncated(monkeypatch):
    mids = [f"m{i}" for i in range(4)]
    diamond = Graph([node("s"), node("t"), *map(node, mids)], [e for m in mids for e in (edge("s", m), edge(m, "t"))])
    monkeypatch.setattr(traverse, "MAX_ENUMERATED", 2)
    out = traverse.paths(diamond, "s", "t", private=True, limit=20)
    assert len(out["paths"]) == 2 and out["truncated"]


# --- MemoryAdjacency ------------------------------------------------------------------------


class Idx:
    def __init__(self):
        self.passages = {"pub": {"scope": "public"}, "priv": {"scope": "private"}}
        self.entities = {
            "x": {"id": "x", "label": "X", "type": "T", "aliases": ["ex"], "docs": ["d"], "scope": "public",
                  "out": [{"p": "r", "o": "y", "passages": ["pub"]}, {"p": "q", "o": "z", "passages": ["priv"]},
                          {"p": "gone", "o": "missing", "passages": ["pub"]}], "in": []},
            "y": {"id": "y", "label": "Y", "type": "T", "aliases": [], "docs": [], "scope": "public",
                  "out": [], "in": [{"p": "r", "s": "x", "passages": ["pub"]}]},
            "z": {"id": "z", "label": "Z", "type": "T", "aliases": [], "docs": [], "scope": "public",
                  "out": [], "in": [{"p": "q", "s": "x", "passages": ["priv"]}]},
        }


def test_memory_adjacency_gives_a_node_with_its_counts():
    n = traverse.MemoryAdjacency(Idx()).node("x")
    assert n["name"] == "X" and n["docs"] == 1 and n["links"] == 3 and n["public"]["type"] == "T"


def test_memory_adjacency_has_no_unknown_node():
    assert traverse.MemoryAdjacency(Idx()).node("nope") is None


def test_a_relation_is_public_when_a_public_passage_states_it():
    adj = traverse.MemoryAdjacency(Idx())
    scopes = {(e["s"], e["o"]): e["scope"] for e, _ in adj.adjacent(["x"], True)}
    assert scopes == {("x", "y"): "public", ("x", "z"): "private"}


def test_memory_adjacency_leaves_private_relations_out_for_a_public_caller():
    assert [(e["s"], e["o"]) for e, _ in traverse.MemoryAdjacency(Idx()).adjacent(["x"], False)] == [("x", "y")]


def test_memory_adjacency_follows_incoming_relations_and_skips_unknown_ids():
    adj = traverse.MemoryAdjacency(Idx())
    assert [(e["s"], e["o"]) for e, _ in adj.adjacent(["y", "nope", "y"], True)] == [("x", "y")]
