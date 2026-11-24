"""The grader's judge is independent, and its agreement with people is reported."""

from knowledge_store.apps import evaluate
from knowledge_store.evaluation.domain.score import agreement

SET = "collection: m\nquestions:\n  - id: q\n    question: Which rocket\n    must: [[a]]\n"


def test_a_judge_that_is_the_model_under_test_is_refused(tmp_path, capsys):
    s = tmp_path / "set.yaml"
    s.write_text(SET, encoding="utf-8")
    code = evaluate.main([str(s), "--lake", str(tmp_path), "--model", "m1", "--grader", "deepeval",
                          "--judge-model", "m1", "--yes"])
    assert code == 2 and "model under test" in capsys.readouterr().out


def test_without_a_judge_named_the_grader_does_not_default_to_the_model_under_test(tmp_path, capsys):
    s = tmp_path / "set.yaml"
    s.write_text(SET, encoding="utf-8")
    code = evaluate.main([str(s), "--lake", str(tmp_path), "--model", "m1", "--grader", "deepeval", "--yes"])
    assert code == 2 and "--judge-model" in capsys.readouterr().out


def test_agreement_with_hand_labels():
    rows = [{"id": "a", "grade": {"verdict": "pass"}}, {"id": "b", "grade": {"verdict": "fail"}},
            {"id": "c", "grade": {"verdict": "pass"}}]
    got = agreement(rows, {"a": "pass", "b": "pass"})
    assert got["labelled"] == 2 and got["agree"] == 1 and got["share"] == 0.5
    assert agreement(rows, {}) is None
