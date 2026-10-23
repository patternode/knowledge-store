"""The Runner port: ask every question and score it, returning (question, result, row) in the
questions' order. Run against the plain loop and, when installed, DeepEval (offline: its metrics
read the rows back and call no model)."""

from __future__ import annotations

import json

import pytest

from knowledge_store.evaluation import Question
from knowledge_store.evaluation.slices.run_set import plain_runner

QS = [Question(id="a", question="?", must=[["Atlas V"]]), Question(id="b", question="?", must=[["Delta"]])]


def ask(q):
    return {"answer": "Atlas V", "abstained": False}


def score_one(q, res):
    return {"id": q.id, "correct": "Delta" not in q.must[0] and bool(res.get("answer")), "score": 1.0, "missing": []}


@pytest.fixture(autouse=True)
def no_confident_key(monkeypatch):
    monkeypatch.delenv("CONFIDENT_API_KEY", raising=False)
    monkeypatch.delenv("API_KEY", raising=False)


@pytest.fixture(params=["plain", "deepeval"])
def runner(request, tmp_path):
    if request.param == "plain":
        return plain_runner
    pytest.importorskip("deepeval")
    from knowledge_store.evaluation import DeepEvalRunner
    return DeepEvalRunner(str(tmp_path / "deepeval"))


def test_every_question_comes_back_in_order(runner):
    out = runner(QS, ask, score_one)
    assert [q.id for q, _, _ in out] == ["a", "b"]


def test_each_triple_holds_the_result_and_its_row(runner):
    (qa, ra, rowa), (qb, rb, rowb) = runner(QS, ask, score_one)
    assert ra["answer"] == "Atlas V" and rowa["correct"] is True and rowb["correct"] is False


def test_the_plain_runner_returns_nothing_for_no_questions():
    assert plain_runner([], ask, score_one) == []


def test_the_deepeval_runner_writes_a_test_run(tmp_path):
    pytest.importorskip("deepeval")
    from knowledge_store.evaluation import DeepEvalRunner
    DeepEvalRunner(str(tmp_path / "deepeval"))(QS, ask, score_one)
    runs = list((tmp_path / "deepeval").glob("test_run_*.json"))
    assert runs
    text = runs[0].read_text()
    assert "Knowledge Store score" in text and json.loads(text)


def test_the_deepeval_runner_records_the_grader_metrics(tmp_path):
    pytest.importorskip("deepeval")
    from knowledge_store.evaluation import DeepEvalRunner

    def graded(q, res):
        return {**score_one(q, res), "grade": {"verdict": "pass", "metrics": {
            "correctness": {"score": 0.9, "passed": True, "reason": "states the fact"}}}}

    DeepEvalRunner(str(tmp_path / "deepeval"))(QS, ask, graded)
    assert "grade: correctness" in next((tmp_path / "deepeval").glob("test_run_*.json")).read_text()


def test_the_deepeval_runner_scores_alike_to_the_plain_loop(tmp_path):
    pytest.importorskip("deepeval")
    from knowledge_store.evaluation import DeepEvalRunner, EvalSet, run
    ev = EvalSet("c", QS, "t")
    plain = run(ev, ask, progress=lambda *_: None)
    recorded = run(ev, ask, runner=DeepEvalRunner(str(tmp_path / "deepeval")), progress=lambda *_: None)
    assert [r["correct"] for r in plain["rows"]] == [r["correct"] for r in recorded["rows"]] == [True, False]


def test_the_deepeval_runner_refuses_to_upload_unasked(tmp_path, monkeypatch):
    pytest.importorskip("deepeval")
    from knowledge_store.evaluation import DeepEvalRunner
    monkeypatch.setenv("CONFIDENT_API_KEY", "confident_us_not-a-key")
    with pytest.raises(RuntimeError, match="Confident AI"):
        DeepEvalRunner(str(tmp_path / "deepeval"))(QS, ask, score_one)


def test_the_deepeval_version_is_pinned():
    from knowledge_store.evaluation.adapters.deepeval_cases import DEEPEVAL_VERSION
    assert DEEPEVAL_VERSION.count(".") == 2


def test_a_row_metric_reads_its_row_and_refuses_a_question_it_has_no_row_for():
    import asyncio
    pytest.importorskip("deepeval")
    from deepeval.errors import MissingTestCaseParamsError
    from deepeval.test_case import LLMTestCase
    from knowledge_store.evaluation.adapters.deepeval_runner import _metric
    Metric = _metric("score", lambda row: (row["score"], row["correct"], "why") if row else None, 0.5)
    m = Metric({"a": {"score": 1.0, "correct": True}})
    assert asyncio.run(m.a_measure(LLMTestCase(name="a", input="?", actual_output="x"))) == 1.0 and m.is_successful()
    with pytest.raises(MissingTestCaseParamsError):
        m.measure(LLMTestCase(name="zz", input="?", actual_output="x"))
