"""The walk ranks a public caller's passages without flowing through private ones."""

from knowledge_store.knowledge_graph.domain import walk as graph


def test_hidden_passages_and_phrases_only_they_reach_are_removed():
    edges = {"p:pub": {"ph:a": 1.0}, "p:priv": {"ph:a": 1.0, "ph:secret": 1.0},
             "ph:a": {"p:pub": 1.0, "p:priv": 1.0}, "ph:secret": {"p:priv": 1.0, "ph:a": 0.5}}
    seen = graph.visible_edges(edges, {"pub"})
    assert set(seen) == {"p:pub", "ph:a"} and seen["ph:a"] == {"p:pub": 1.0}
