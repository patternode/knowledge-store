"""The Runner port: ask every question and score it, returning (question, result, row) in the
questions' order. Run against the plain loop and, when installed, Inspect AI (offline: it runs
on Inspect's mock model and the solver never calls it)."""

from __future__ import annotations

import pytest

from knowledge_store.evaluation import Question
from knowledge_store.evaluation.slices.run_set import plain_runner

QS = [Question(id="a", question="?", must=[["Atlas V"]]), Question(id="b", question="?", must=[["Delta"]])]


def ask(q):
    return {"answer": "Atlas V", "abstained": False}


def score_one(q, res):
    return {"id": q.id, "correct": "Delta" not in q.must[0] and bool(res.get("answer")), "score": 1.0, "missing": []}


@pytest.fixture(params=["plain", "inspect"])
def runner(request, tmp_path):
    if request.param == "plain":
        return plain_runner
    pytest.importorskip("inspect_ai")
    from knowledge_store.evaluation import InspectRunner
    return InspectRunner(str(tmp_path / "logs"), max_samples=2)


def test_every_question_comes_back_in_order(runner):
    out = runner(QS, ask, score_one)
    assert [q.id for q, _, _ in out] == ["a", "b"]


def test_each_triple_holds_the_result_and_its_row(runner):
    (qa, ra, rowa), (qb, rb, rowb) = runner(QS, ask, score_one)
    assert ra["answer"] == "Atlas V" and rowa["correct"] is True and rowb["correct"] is False


def test_the_plain_runner_returns_nothing_for_no_questions():
    assert plain_runner([], ask, score_one) == []


def test_the_inspect_runner_writes_a_log(tmp_path):
    pytest.importorskip("inspect_ai")
    from knowledge_store.evaluation import InspectRunner
    InspectRunner(str(tmp_path / "logs"))(QS, ask, score_one)
    assert list((tmp_path / "logs").glob("*.eval"))


def test_the_inspect_runner_scores_alike_to_the_plain_loop(tmp_path):
    pytest.importorskip("inspect_ai")
    from knowledge_store.evaluation import EvalSet, InspectRunner, run
    ev = EvalSet("c", QS, "t")
    plain = run(ev, ask, progress=lambda *_: None)
    inspected = run(ev, ask, runner=InspectRunner(str(tmp_path / "logs")), progress=lambda *_: None)
    assert [r["correct"] for r in plain["rows"]] == [r["correct"] for r in inspected["rows"]] == [True, False]


def test_the_inspect_version_is_pinned():
    from knowledge_store.evaluation.adapters.inspect_runner import INSPECT_VERSION
    assert INSPECT_VERSION.count(".") == 2
