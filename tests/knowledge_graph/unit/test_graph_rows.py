"""Nodes and edges in the shape a property-graph backend loads."""

from __future__ import annotations

from knowledge_store.knowledge_graph.domain.graph_rows import rows, stamp


class Spec:
    """The two things rows() asks of an ontology: its classes and each one's ancestors."""

    classes = {"Mission": None, "Probe": None, "SpaceAgency": None}
    parents = {"Probe": {"Mission"}}

    def ancestors(self, t):
        return {t, *self.parents.get(t, set())}


BASE = "https://example.org/data/"
PASSAGES = {"p1": {"scope": "public"}, "p2": {"scope": "private"}}


def entity(**kw):
    e = {"id": "entity/Probe/alpha", "label": "Alpha", "type": "Probe", "types": ["Probe"], "aliases": ["A"],
         "docs": ["d1"], "out": [], "in": [], "passages": ["p1"], "attributes": [], "scope": "public"}
    e.update(kw)
    return e


def test_stamp_keeps_the_digits_of_a_timestamp():
    assert stamp("2026-09-30T12:34:56+00:00") == "20260930123456"


def test_a_node_carries_entity_and_a_label_per_class_and_ancestor():
    nodes, _ = rows([entity()], PASSAGES, Spec(), BASE)
    assert nodes[0]["labels"][0] == "Entity" and set(nodes[0]["labels"][1:]) == {"Mission", "Probe"}


def test_a_node_carries_its_iri_name_scope_and_counts():
    props = rows([entity(out=[{"p": "launchedBy", "o": "x", "passages": ["p1"]}])], PASSAGES, Spec(), BASE)[0][0]["props"]
    assert props["iri"] == BASE + "entity/Probe/alpha" and props["name"] == "Alpha"
    assert props["docs"] == 1 and props["links"] == 1 and props["scope"] == "public" and props["mentioned_in"] == ["p1"]


def test_an_entity_without_a_scope_is_public():
    e = entity()
    del e["scope"]
    assert rows([e], PASSAGES, Spec(), BASE)[0][0]["props"]["scope"] == "public"


def test_what_public_documents_say_is_flattened():
    e = entity(public={"type": "Probe", "types": ["Probe"], "aliases": ["A"], "docs": 1, "links": 0})
    props = rows([e], PASSAGES, Spec(), BASE)[0][0]["props"]
    assert (props["public_type"], props["public_types"], props["public_docs"]) == ("Probe", ["Probe"], 1)


def test_attributes_become_list_properties_with_their_passages():
    e = entity(attributes=[{"p": "launchYear", "v": "2020", "passages": ["p1"]},
                           {"p": "launchYear", "v": "2021", "passages": ["p1", "p2"]}])
    props = rows([e], PASSAGES, Spec(), BASE)[0][0]["props"]
    assert props["launchYear"] == ["2020", "2021"] and props["launchYear__passages"] == ["p1", "p2"]


def test_a_reserved_attribute_name_is_prefixed():
    props = rows([entity(attributes=[{"p": "id", "v": "x", "passages": []}])], PASSAGES, Spec(), BASE)[0][0]["props"]
    assert props["id"] == "entity/Probe/alpha" and props["a_id"] == ["x"]


def test_an_edge_takes_its_relation_type_and_is_public_when_a_public_passage_states_it():
    e = entity(out=[{"p": "launchedBy", "o": "o1", "passages": ["p2", "p1"]}, {"p": "studies", "o": "o2", "passages": ["p2"]}])
    _, edges = rows([e], PASSAGES, Spec(), BASE)
    assert [(x["type"], x["props"]["scope"]) for x in edges] == [("LAUNCHED_BY", "public"), ("STUDIES", "private")]
    assert edges[0]["s"] == "entity/Probe/alpha" and edges[0]["o"] == "o1" and edges[0]["props"]["p"] == "launchedBy"
