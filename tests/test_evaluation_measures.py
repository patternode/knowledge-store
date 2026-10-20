"""The Evaluation context's measures (patternode-architecture ADR-048): false answers and cited
hedges told apart, unsupported claims counted on any question, figures matched at the answer's
own rounding, citation precision and recall, paraphrase families, the baseline gate, and the
runners. Everything runs offline."""

from __future__ import annotations

import pytest

from knowledge_store.evaluation import (DirRunStore, EvalSet, LexicalVerifier, Question, Rules, compare, gate, matches,
                                        report, run, score, summarise)
from knowledge_store.evaluation.domain.score import wilson


def q(**kw):
    return Question(**{"id": "x", "question": "Where was Moriarty born?", **kw})


def reply(text, *, claims=(), sources=(), abstained=False, gaps=None):
    r = {"answer": text, "abstained": abstained, "claims": list(claims), "sources": list(sources),
         "grounding": {"claims_proposed": len(claims), "claims_shown": len(claims)}}
    if gaps is not None:
        r["gaps"] = gaps
    return r


UNANSWERABLE = dict(kind="unanswerable", answerable=False, must_not=["Ireland", "Dublin"])


def test_a_cited_hedge_on_an_unanswerable_question_is_a_right_decline():
    hedge = reply("The stories do not say where he was born; he is described as a man of good birth [1].",
                  claims=[{"text": "He is described as a man of good birth.", "sources": [1]}],
                  sources=[{"n": 1, "text": "a man of good birth and excellent education"}], gaps=["birthplace"])
    r = score(q(**UNANSWERABLE), hedge)
    assert r["correct"] and r["declined"] and not r["false_answer"]


def test_an_invented_fact_on_an_unanswerable_question_is_a_false_answer():
    made_up = reply("Moriarty was born in Ireland [1].", claims=[{"text": "Moriarty was born in Ireland.", "sources": [1]}],
                    sources=[{"n": 1, "text": "a man of good birth"}], gaps=[])
    r = score(q(**UNANSWERABLE), made_up)
    assert not r["correct"] and r["false_answer"] and r["forbidden"] == ["Ireland"]


def test_an_error_is_never_a_right_decline():
    r = score(q(**UNANSWERABLE), {"error": "model unavailable", "abstained": True})
    assert not r["correct"] and not r["false_answer"]


def test_without_gaps_the_reply_text_says_whether_it_declined():
    assert score(q(**UNANSWERABLE), reply("The sources do not say where he was born."))["declined"]
    assert not score(q(**UNANSWERABLE), reply("He was born in Kent."))["declined"]


def test_unsupported_claims_count_on_answerable_questions_too():
    verifier = LexicalVerifier()
    src = [{"n": 1, "text": "Juno launched on an Atlas V 551 from Cape Canaveral in August 2011."}]
    claims = [{"text": "Juno launched on an Atlas V 551.", "sources": [1]},
              {"text": "Juno was built in Toulouse by a European consortium.", "sources": [1]}]
    ev = EvalSet("missions", [Question(id="q1", question="Which rocket launched Juno?", must=[["Atlas V 551"]])], "t")
    out = run(ev, lambda _: reply("Juno launched on an Atlas V 551 [1]. It was built in Toulouse [1].", claims=claims,
                                  sources=src), verifier=verifier, progress=lambda *_: None)
    row = out["rows"][0]
    assert row["correct"] and row["unsupported"] == 1 and row["supported_share"] == 0.5
    assert out["summary"]["all"]["unsupported_claims"] == 1


def test_a_claim_with_a_number_its_source_does_not_state_is_unsupported():
    ok, _ = LexicalVerifier().grounded("?", "Revenue was $3.4 billion.", ["Revenue was $3.1 billion for the quarter."])
    assert not ok
    ok, _ = LexicalVerifier().grounded("?", "Revenue was $3.1 billion.", ["Revenue was $3.1 billion for the quarter."])
    assert ok


@pytest.mark.parametrize("text,expected,ok", [
    ("Revenue was $94.9 billion.", 94_930_000_000, True),     # stated to a tenth of a billion
    ("Revenue was $2.2 million.", 2_240_000, True),           # within half of 0.1 million
    ("Revenue was $2.2 million.", 2_260_000, False),
    ("Revenue reached $2.6 billion, up from $2.4 billion.", 3_000_000_000, False),  # a round expected figure no longer widens the window
    ("Net income was 3,000,000,000 dollars.", 3_000_000_000, True),
    ("In 2024 the company grew.", 2024, False),               # a year is not a figure
    ("EPS was (0.12).", -0.12, True),
])
def test_figures_match_at_the_answers_own_rounding(text, expected, ok):
    assert matches(text, expected) is ok


def test_a_set_can_give_a_relative_tolerance():
    assert matches("about 3.1 billion", 3_000_000_000, tolerance=0.05)
    assert not matches("about 3.4 billion", 3_000_000_000, tolerance=0.05)


def test_figures_count_as_facts():
    fig = Question(id="f", question="Revenue?", figures=[{"value": 94_930_000_000}])
    assert score(fig, reply("It was $94.9 billion."))["correct"]
    assert score(fig, reply("It was $90 billion."))["missing"] == ["94930000000"]


def test_citation_precision_and_recall():
    qn = Question(id="c", question="?", must=[["Atlas"]], sources=["outer-planets/juno.json", "mars/curiosity.html"])
    r = score(qn, reply("Atlas", sources=[{"name": "juno.json"}, {"name": "dawn.md"}]))
    assert r["citation_precision"] == 0.5 and r["citation_recall"] == 0.5 and r["source_hit"]


def test_paraphrase_families_should_be_answered_alike():
    rows = [{"id": "a", "kind": "lookup", "family": "juno", "correct": True, "score": 1, "grounded": None, "source_hit": None},
            {"id": "b", "kind": "lookup", "family": "juno", "correct": False, "score": 0, "grounded": None, "source_hit": None},
            {"id": "c", "kind": "lookup", "family": "dawn", "correct": True, "score": 1, "grounded": None, "source_hit": None},
            {"id": "d", "kind": "lookup", "family": "dawn", "correct": True, "score": 1, "grounded": None, "source_hit": None}]
    fam = summarise(rows)["families"]
    assert fam == {"families": 2, "consistent": 0.5, "split": ["juno"]}


def test_small_sets_report_a_wide_interval():
    lo, hi = wilson(8, 10)
    assert lo < 0.5 < 0.8 < hi


def _run(correct: dict[str, bool], false_answers=0):
    rows = [{"id": i, "kind": "lookup", "correct": c, "score": float(c), "grounded": None, "source_hit": None,
             "false_answer": False} for i, c in correct.items()]
    out = {"set": "s", "collection": "c", "rows": rows, "summary": summarise(rows)}
    out["summary"]["all"]["false_answers"] = false_answers
    return out


def test_the_gate_fails_on_a_regression_and_names_it():
    g = compare(_run({"a": True, "b": False}), _run({"a": True, "b": True}))
    assert not g.passed and g.regressions == ["b"] and "b" in g.failures[0]


def test_the_gate_passes_an_improvement_and_can_allow_a_drop():
    assert compare(_run({"a": True, "b": True}), _run({"a": True, "b": False})).passed
    assert compare(_run({"a": True, "b": False}), _run({"a": True, "b": True}),
                   Rules(max_accuracy_drop=0.5, allow_regressions=1)).passed


def test_the_gate_fails_when_false_answers_rise():
    g = compare(_run({"a": True}, false_answers=1), _run({"a": True}))
    assert not g.passed and "false answers" in g.failures[0]


def test_a_baseline_is_kept_only_on_purpose(tmp_path):
    store = DirRunStore(tmp_path)
    first = _run({"a": True, "b": True})
    assert gate(first, store) is None and store.baseline("s") is None
    assert gate(first, store, keep=True) is None and store.baseline("s")["rows"][0]["id"] == "a"
    worse = _run({"a": True, "b": False})
    g = gate(worse, store, keep=True)
    assert not g.passed and store.baseline("s")["rows"][1]["correct"] is True   # a failing run never becomes the baseline
    assert "Release gate" in report({**worse, "when": "now", "tokens": {"inputTokens": 0, "outputTokens": 0}}, g)


def test_a_token_budget_stops_the_run_before_the_next_question():
    ev = EvalSet("c", [Question(id=f"q{i}", question="?", must=[["x"]]) for i in range(3)], "t")
    asked = []

    def ask(qn):
        asked.append(qn.id)
        return {**reply("x"), "usage": {"inputTokens": 600, "outputTokens": 0}}
    out = run(ev, ask, max_tokens=1000, progress=lambda *_: None)
    assert asked == ["q0", "q1"] and "budget" in out["rows"][2]["error"]


def test_truth_sources_can_fail_an_answer_the_text_checks_passed():
    class Canary:
        name = "canary"

        def check(self, question, result):
            leaked = "Jane Analyst" in (result.get("answer") or "")
            return {"ok": not leaked, "detail": "names a private analyst" if leaked else ""}
    ev = EvalSet("c", [Question(id="p", question="?", must=[["guidance"]])], "t")
    out = run(ev, lambda _: reply("guidance was raised, said Jane Analyst"), truth=[Canary()], progress=lambda *_: None)
    assert not out["rows"][0]["correct"] and out["rows"][0]["truth"]["canary"]["ok"] is False


def test_the_inspect_runner_scores_alike_offline(tmp_path):
    pytest.importorskip("inspect_ai")
    from knowledge_store.evaluation import InspectRunner
    ev = EvalSet("c", [Question(id="a", question="?", must=[["Atlas V"]]), Question(id="b", question="?", must=[["Delta"]])], "t")
    plain = run(ev, lambda _: reply("Atlas V"), progress=lambda *_: None)
    inspected = run(ev, lambda _: reply("Atlas V"), runner=InspectRunner(str(tmp_path / "logs")), progress=lambda *_: None)
    assert [r["correct"] for r in plain["rows"]] == [r["correct"] for r in inspected["rows"]] == [True, False]
    assert list((tmp_path / "logs").glob("*.eval"))
