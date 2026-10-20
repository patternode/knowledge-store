"""The release gate's comparison of a run with its baseline: deterministic, and every failure named."""

from __future__ import annotations

from knowledge_store.evaluation.domain.compare import Gate, Rules, compare
from knowledge_store.evaluation.domain.score import summarise


def run_of(correct: dict[str, bool], **summary):
    rows = [{"id": i, "kind": "lookup", "correct": c, "score": float(c), "grounded": None, "source_hit": None}
            for i, c in correct.items()]
    s = summarise(rows)
    s["all"].update(summary)
    return {"set": "s", "rows": rows, "summary": s}


def test_an_identical_run_passes_with_nothing_to_report():
    g = compare(run_of({"a": True, "b": False}), run_of({"a": True, "b": False}))
    assert isinstance(g, Gate) and g.passed and g.failures == [] and g.regressions == [] and g.fixed == []
    assert g.deltas == {"accuracy": 0.0, "false_answers": 0, "false_abstentions": 0}


def test_a_question_right_before_and_wrong_now_is_a_named_regression():
    g = compare(run_of({"a": True, "b": False}), run_of({"a": True, "b": True}))
    assert not g.passed and g.regressions == ["b"] and "b" in g.failures[0]


def test_a_question_wrong_before_and_right_now_is_fixed_and_passes():
    g = compare(run_of({"a": True, "b": True}), run_of({"a": True, "b": False}))
    assert g.passed and g.fixed == ["b"] and g.deltas["accuracy"] == 0.5


def test_regressions_can_be_allowed_up_to_a_count():
    now, base = run_of({"a": False, "b": True, "c": True}), run_of({"a": True, "b": True, "c": True})
    assert not compare(now, base, Rules(max_accuracy_drop=1.0)).passed
    assert compare(now, base, Rules(max_accuracy_drop=1.0, allow_regressions=1)).passed


def test_an_accuracy_drop_beyond_the_allowance_fails():
    now, base = run_of({"a": False, "b": True}), run_of({"a": True, "b": True})
    g = compare(now, base, Rules(allow_regressions=5, max_accuracy_drop=0.4))
    assert not g.passed and any("accuracy fell by 0.500" in f for f in g.failures)
    assert compare(now, base, Rules(allow_regressions=5, max_accuracy_drop=0.5)).passed


def test_accuracy_is_compared_on_the_shared_questions_only():
    g = compare(run_of({"a": True, "new": False}), run_of({"a": True}))
    assert g.passed and g.deltas["accuracy"] == 0.0


def test_a_rise_in_false_answers_fails():
    g = compare(run_of({"a": True}, false_answers=2), run_of({"a": True}, false_answers=1))
    assert not g.passed and g.failures == ["false answers rose by 1"]
    assert compare(run_of({"a": True}, false_answers=2), run_of({"a": True}, false_answers=1), Rules(max_false_answer_rise=1)).passed


def test_a_fall_in_false_answers_passes():
    assert compare(run_of({"a": True}, false_answers=0), run_of({"a": True}, false_answers=3)).passed


def test_unsupported_claims_are_compared_only_when_both_runs_verified_claims():
    assert "unsupported_claims" not in compare(run_of({"a": True}), run_of({"a": True})).deltas
    g = compare(run_of({"a": True}, unsupported_claims=4), run_of({"a": True}, unsupported_claims=1))
    assert not g.passed and g.deltas["unsupported_claims"] == 3 and "unsupported claims rose by 3" in g.failures
    assert compare(run_of({"a": True}, unsupported_claims=4), run_of({"a": True}, unsupported_claims=1),
                   Rules(max_unsupported_rise=3)).passed


def test_false_abstentions_are_reported_but_do_not_fail():
    g = compare(run_of({"a": True}, false_abstentions=2), run_of({"a": True}))
    assert g.passed and g.deltas["false_abstentions"] == 2


def test_a_baseline_question_that_was_not_run_fails():
    g = compare(run_of({"a": True}), run_of({"a": True, "b": True}))
    assert not g.passed and "1 baseline question(s) were not run: b" in g.failures


def test_a_run_with_no_shared_questions_compares_at_zero():
    g = compare(run_of({"x": True}), run_of({}))
    assert g.passed and g.deltas["accuracy"] == 0.0


def test_missing_counts_are_read_as_zero():
    now, base = run_of({"a": True}), run_of({"a": True})
    now["summary"]["all"]["false_answers"] = None
    assert compare(now, base).deltas["false_answers"] == 0
