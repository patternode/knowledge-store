"""Retrieval measures over what the tools returned."""

from knowledge_store.evaluation import Question, score
from knowledge_store.evaluation.domain import compare, retrieval
from knowledge_store.evaluation.domain.score import summarise

Q = dict(id="q", question="Which rocket launched Juno?", must=[["Atlas V"]], sources=["juno.json", "atlas.json"])


def hits(*docs):
    return [{"tool": "search_passages", "kind": "passages", "rank": i, "id": f"p{i}", "doc": d}
            for i, d in enumerate(docs, 1)]


def test_recall_precision_and_reciprocal_rank_count_what_was_retrieved():
    m = retrieval.measures(["juno.json", "atlas.json"], {}, hits("x.json", "juno.json", "y.json"), set(), by_passage=False)
    assert m["recall_at_5"] == 0.5 and m["precision_at_5"] == round(1 / 3, 3) and m["reciprocal_rank"] == 0.5


def test_retrieved_but_not_cited_is_an_answering_fault():
    m = retrieval.measures(["juno.json"], {}, hits("juno.json"), {"other.json"}, by_passage=False)
    assert m["recall_at_5"] == 1.0 and m["retrieved_not_cited"] == ["juno.json"]


def test_graded_relevance_gives_ndcg():
    best = retrieval.measures([], {"p1": 2, "p2": 1}, hits("a", "b"), set(), by_passage=True)
    worse = retrieval.measures([], {"p1": 2, "p2": 1}, list(reversed(hits("a", "b"))), set(), by_passage=True)
    assert best["ndcg_at_10"] == 1.0 and worse["ndcg_at_10"] < 1.0


def test_the_scorer_and_summary_carry_retrieval_and_the_gate_watches_recall():
    row = score(Question(**Q), {"answer": "An Atlas V.", "retrieved": hits("juno.json", "atlas.json"),
                                "sources": [{"name": "juno.json"}]})
    assert row["recall_at_10"] == 1.0 and row["retrieved_not_cited"] == ["atlas.json"]
    worse = score(Question(**Q), {"answer": "An Atlas V.", "retrieved": hits("x.json"), "sources": []})
    then = {"rows": [row], "summary": summarise([row])}
    now = {"rows": [{**worse, "correct": True}], "summary": summarise([worse])}
    gate = compare.compare(now, then)
    assert not gate.passed and any("recall" in f for f in gate.failures)


def test_a_result_without_retrieved_items_is_scored_as_before():
    row = score(Question(**Q), {"answer": "An Atlas V."})
    assert "recall_at_10" not in row
