"""The walk's domain: the graph a set of facts builds, the spread of a question over it, and the
passages that come out on top."""
from __future__ import annotations

from knowledge_store.knowledge_graph.domain import walk

FACTS = [
    {"s": "Mission Alpha", "p": "launched by", "o": "Agency Nova", "pid": "p1", "doc": "alpha", "grounded": True},
    {"s": "Agency Nova", "p": "based in", "o": "Lyon", "pid": "p2", "doc": "nova", "grounded": True},
    {"s": "Mission Beta", "p": "launched by", "o": "Agency Orbis", "pid": "p3", "doc": "beta", "grounded": True},
    {"s": "Mission Beta", "p": "carries", "o": "Instrument Lux", "pid": "p3", "doc": "beta", "grounded": False},
]


def test_phrase_keys_fold_case_punctuation_and_spacing():
    assert walk.phrase_key("Agency  Nova") == walk.phrase_key("agency-nova") == "agency nova"
    assert walk.phrase_key("") == "" and walk.phrase_key("  ") == ""


def test_the_graph_joins_facts_passages_and_synonyms():
    g = walk.build_graph(FACTS, [("Agency Nova", "Nova Agency", 0.9), ("Agency Nova", "unknown thing", 0.95)])
    assert set(g["phrases"]) == {"mission alpha", "agency nova", "lyon", "mission beta", "agency orbis", "instrument lux"}
    assert g["passages"] == {"p1": "alpha", "p2": "nova", "p3": "beta"}
    e = g["edges"]
    assert e["e:mission alpha"]["e:agency nova"] == 1.0 and e["e:agency nova"]["e:mission alpha"] == 1.0
    assert e["p:p1"]["e:mission alpha"] == 1.0 and e["e:lyon"]["p:p2"] == 1.0
    assert e["e:mission beta"]["e:instrument lux"] == 0.5      # ungrounded facts weigh half
    assert "e:nova agency" not in e                              # a synonym must name two known phrases
    g2 = walk.build_graph(FACTS, [("Mission Alpha", "mission-beta", 0.85)])
    assert g2["edges"]["e:mission alpha"]["e:mission beta"] == 0.85  # two known phrases are joined by their similarity


def test_a_fact_without_a_phrase_or_a_passage_is_ignored():
    g = walk.build_graph([{"s": "", "p": "x", "o": "y", "pid": "p"}, {"s": "a", "p": "x", "o": "b", "pid": ""}])
    assert g["phrases"] == {} and g["passages"] == {} and g["edges"] == {}


def test_pagerank_spreads_from_the_seeds_to_what_they_touch():
    g = walk.build_graph(FACTS)
    scores = walk.personalized_pagerank(g["edges"], {"e:mission alpha": 1.0})
    assert abs(sum(scores.values()) - 1.0) < 1e-6
    assert scores["e:mission alpha"] > scores["e:agency nova"] > scores["e:lyon"] > 0
    assert scores["p:p1"] > scores["p:p2"] > 0 and scores.get("p:p3", 0.0) == 0.0   # Beta is not connected to Alpha


def test_pagerank_without_seeds_or_with_a_seed_off_the_graph():
    g = walk.build_graph(FACTS)
    assert walk.personalized_pagerank(g["edges"], {}) == {} and walk.personalized_pagerank(g["edges"], {"x": 0.0}) == {}
    lone = walk.personalized_pagerank(g["edges"], {"e:nowhere": 1.0})
    assert lone == {"e:nowhere": 1.0}


def test_seeds_take_the_best_phrases_and_every_passage_lightly():
    hits = [(FACTS[0], 0.9), (FACTS[1], 0.7)]
    seeds = walk.seeds_from(hits, [("p9", 0.5), ("p8", 0.0)], passage_weight=0.1, top_phrases=2)
    assert seeds["e:mission alpha"] == 0.9 and seeds["e:agency nova"] == 0.8 and "e:lyon" not in seeds
    assert seeds["p:p9"] == 0.05 and "p:p8" not in seeds


def test_the_top_passages_are_the_best_scored_in_the_allowed_set():
    scores = {"p:a": 0.3, "p:b": 0.5, "e:x": 0.9, "p:c": 0.0, "p:d": 0.5}
    assert walk.rank_passages(scores, limit=2) == [("b", 0.5), ("d", 0.5)]
    assert walk.rank_passages(scores, allowed={"a", "c"}) == [("a", 0.3)]
