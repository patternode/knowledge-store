"""Running a set (evaluation/slices/run_set.py) through fakes of its ports: a fake Answerer, the
LexicalVerifier, truth sources, a grader and runners. Nothing calls a model."""

from __future__ import annotations

import datetime as dt

from knowledge_store.evaluation import EvalSet, LexicalVerifier, Question, run
from knowledge_store.evaluation.slices.run_set import claim_sources, plain_runner, tokens, verify

FIXED = dt.datetime(2026, 10, 20, 9, 30, tzinfo=dt.UTC)


def quiet(**kw):
    return {"progress": lambda *_: None, "now": lambda: FIXED, **kw}


def reply(text, *, claims=(), sources=(), usage=None, **extra):
    r = {"answer": text, "abstained": False, "claims": list(claims), "sources": list(sources),
         "grounding": {"claims_proposed": len(claims), "claims_shown": len(claims)}, **extra}
    if usage:
        r["usage"] = usage
    return r


def evset(*qs):
    return EvalSet("missions", list(qs) or [Question(id="q1", question="Which rocket?", must=[["Atlas V"]])], "space")


class FakeAnswerer:
    def __init__(self, replies):
        self.replies, self.asked = replies, []

    def __call__(self, q):
        self.asked.append(q.id)
        r = self.replies[q.id]
        if isinstance(r, Exception):
            raise r
        return r


def test_a_run_records_the_set_the_collection_and_when_it_ran():
    out = run(evset(), FakeAnswerer({"q1": reply("Atlas V")}), **quiet())
    assert (out["set"], out["collection"], out["when"]) == ("space", "missions", "2026-10-20T09:30:00+00:00")


def test_every_question_is_asked_once_and_scored_in_order():
    ev = evset(Question(id="b", question="?", must=[["x"]]), Question(id="a", question="?", must=[["y"]]))
    ask = FakeAnswerer({"a": reply("y"), "b": reply("nope")})
    out = run(ev, ask, **quiet())
    assert ask.asked == ["b", "a"] and [r["id"] for r in out["rows"]] == ["b", "a"]
    assert [r["correct"] for r in out["rows"]] == [False, True] and out["summary"]["all"]["correct"] == 1


def test_only_asks_the_named_questions():
    ev = evset(Question(id="a", question="?", must=[["x"]]), Question(id="b", question="?", must=[["x"]]))
    ask = FakeAnswerer({"a": reply("x"), "b": reply("x")})
    out = run(ev, ask, only=["b"], **quiet())
    assert ask.asked == ["b"] and [r["id"] for r in out["rows"]] == ["b"]


def test_a_failing_question_scores_zero_and_the_run_goes_on():
    ev = evset(Question(id="a", question="?", must=[["x"]]), Question(id="b", question="?", must=[["x"]]))
    out = run(ev, FakeAnswerer({"a": RuntimeError("model down"), "b": reply("x")}), **quiet())
    assert out["rows"][0]["error"] == "RuntimeError: model down" and not out["rows"][0]["correct"]
    assert out["rows"][1]["correct"] and out["summary"]["all"]["errors"] == 1


def test_a_long_error_message_is_cut():
    out = run(evset(), FakeAnswerer({"q1": ValueError("x" * 1000)}), **quiet())
    assert len(out["rows"][0]["error"]) < 330


def test_results_keep_each_question_and_reply_without_timing_internals():
    out = run(evset(Question(id="q1", question="Which rocket?", must=[["Atlas V"]], expected="Atlas V")),
              FakeAnswerer({"q1": reply("Atlas V")}), **quiet())
    res = out["results"][0]
    assert res["id"] == "q1" and res["question"] == "Which rocket?" and res["expected"] == "Atlas V"
    assert res["result"]["answer"] == "Atlas V" and "_seconds" not in res["result"]
    assert out["rows"][0]["seconds"] is not None


def test_tokens_are_totalled_from_what_the_answers_report():
    ev = evset(Question(id="a", question="?", must=[["x"]]), Question(id="b", question="?", must=[["x"]]))
    out = run(ev, FakeAnswerer({"a": reply("x", usage={"inputTokens": 10, "outputTokens": 2}), "b": reply("x")}), **quiet())
    assert out["tokens"] == {"inputTokens": 10, "outputTokens": 2}
    assert tokens([{"usage": None}, {}]) == {"inputTokens": 0, "outputTokens": 0}


def test_a_token_budget_skips_questions_once_spent():
    ev = evset(*[Question(id=f"q{i}", question="?", must=[["x"]]) for i in range(3)])
    ask = FakeAnswerer({f"q{i}": reply("x", usage={"inputTokens": 600, "outputTokens": 0}) for i in range(3)})
    out = run(ev, ask, max_tokens=1000, **quiet())
    assert ask.asked == ["q0", "q1"] and "budget" in out["rows"][2]["error"] and not out["rows"][2]["correct"]


def test_progress_reports_each_question():
    lines = []
    run(evset(), FakeAnswerer({"q1": reply("Atlas V")}), progress=lines.append, now=lambda: FIXED)
    assert len(lines) == 1 and lines[0].startswith("q1 lookup") and "PASS" in lines[0]


def test_without_a_verifier_no_claim_is_checked():
    out = run(evset(), FakeAnswerer({"q1": reply("Atlas V", claims=[{"text": "made up", "sources": []}])}), **quiet())
    assert out["rows"][0]["verdicts"] is None and out["rows"][0]["unsupported"] is None


def test_a_verifier_rejects_a_claim_its_source_does_not_support():
    src = [{"n": 1, "text": "Juno launched on an Atlas V 551 in August 2011."}]
    claims = [{"text": "Juno launched on an Atlas V 551.", "sources": [1]},
              {"text": "Juno was built in Toulouse by a consortium.", "sources": [1]}]
    out = run(evset(), FakeAnswerer({"q1": reply("Atlas V", claims=claims, sources=src)}), verifier=LexicalVerifier(), **quiet())
    row = out["rows"][0]
    assert row["correct"] and row["unsupported"] == 1 and [v["supported"] for v in row["verdicts"]] == [True, False]


def test_a_claim_citing_nothing_readable_is_unsupported_without_asking_the_verifier():
    class Never:
        def grounded(self, *a):
            raise AssertionError("not called")
    v = verify(Question(id="q", question="?"), reply("x", claims=[{"text": "c", "sources": [9]}]), Never())
    assert v == [{"claim": "c", "supported": False, "score": None, "why": "cites nothing readable"}]


def test_no_claim_is_verified_on_an_abstention_or_an_error():
    v = LexicalVerifier()
    assert verify(Question(id="q", question="?"), {"abstained": True, "claims": [{"text": "c"}]}, v) is None
    assert verify(Question(id="q", question="?"), {"error": "x", "claims": [{"text": "c"}]}, v) is None


def test_a_claim_rests_on_passages_cells_and_figures():
    result = {"sources": [{"n": 1, "text": "passage one"}, {"n": 2}]}
    claim = {"sources": [1, 2, 3], "citations": [{"cell_id": "c1", "column": "year", "value": 2011},
                                                {"cell_id": "c2", "value": "x"}, {"cell_id": "c3", "value": None},
                                                {"metric_id": "m", "figure": 42}, {"metric_id": "m2", "figure": None}]}
    assert claim_sources(result, claim) == ["passage one", "year: 2011", "value: x", "42"]


def test_a_truth_source_that_fails_makes_the_answer_wrong():
    class Canary:
        name = "canary"

        def check(self, question, result):
            return {"ok": False, "detail": "names a private analyst"}
    out = run(evset(), FakeAnswerer({"q1": reply("Atlas V")}), truth=[Canary()], **quiet())
    row = out["rows"][0]
    assert not row["correct"] and row["score"] == 0.0 and row["truth"]["canary"]["ok"] is False


def test_a_truth_source_with_nothing_to_say_changes_nothing():
    class Silent:
        name = "silent"

        def check(self, question, result):
            return {"ok": None, "detail": ""}
    row = run(evset(), FakeAnswerer({"q1": reply("Atlas V")}), truth=[Silent()], **quiet())["rows"][0]
    assert row["correct"] and row["truth"] == {"silent": {"ok": None, "detail": ""}}


def test_without_truth_sources_the_row_says_none():
    assert run(evset(), FakeAnswerer({"q1": reply("Atlas V")}), **quiet())["rows"][0]["truth"] is None


def test_a_grader_is_reported_beside_the_score_never_in_it():
    class Harsh:
        def grade(self, question, result):
            return {"verdict": "fail", "explanation": "too short"}
    row = run(evset(), FakeAnswerer({"q1": reply("Atlas V")}), grader=Harsh(), **quiet())["rows"][0]
    assert row["correct"] and row["grade"]["verdict"] == "fail"


def test_a_grader_is_not_asked_about_an_error():
    class Never:
        def grade(self, *a):
            raise AssertionError("not called")
    row = run(evset(), FakeAnswerer({"q1": RuntimeError("x")}), grader=Never(), **quiet())["rows"][0]
    assert "grade" not in row


def test_a_runner_drives_the_questions_and_its_order_is_kept():
    seen = []

    def backwards(questions, ask, score_one):
        seen.append([q.id for q in questions])
        return [(q, res, score_one(q, res)) for q in reversed(questions) for res in [ask(q)]]
    ev = evset(Question(id="a", question="?", must=[["x"]]), Question(id="b", question="?", must=[["x"]]))
    out = run(ev, FakeAnswerer({"a": reply("x"), "b": reply("x")}), runner=backwards, **quiet())
    assert seen == [["a", "b"]] and [r["id"] for r in out["rows"]] == ["b", "a"]


def test_the_plain_runner_asks_then_scores_each_question():
    calls = []
    out = plain_runner([Question(id="a", question="?")], lambda q: calls.append(("ask", q.id)) or {"x": 1},
                       lambda q, r: calls.append(("score", q.id)) or {"id": q.id})
    assert calls == [("ask", "a"), ("score", "a")] and out[0][1] == {"x": 1}


def test_tool_calls_are_counted():
    row = run(evset(), FakeAnswerer({"q1": reply("Atlas V", tool_calls=[{}, {}])}), **quiet())["rows"][0]
    assert row["tool_calls"] == 2


def test_the_default_clock_is_utc():
    out = run(evset(), FakeAnswerer({"q1": reply("Atlas V")}), progress=lambda *_: None)
    assert out["when"].endswith("+00:00")
