"""Judged questions: the set states no fact, so truth sources or a grader say whether the answer is right."""

import pytest

from knowledge_store.evaluation import Question, parse, position, score, summarise


def judged(**kw):
    return Question(id="j1", question="How did margins move?", judged=True, **kw)


def test_a_judged_question_needs_no_stated_fact():
    s = parse({"collection": "c", "questions": [{"id": "j1", "question": "Why?", "judged": True}]})
    assert s.questions[0].judged and s.questions[0].must == []


def test_an_answerable_question_with_no_fact_and_not_judged_is_refused():
    with pytest.raises(ValueError, match="judged: true"):
        parse({"collection": "c", "questions": [{"id": "q", "question": "Why?"}]})


def test_a_question_carries_context_its_truth_sources_read():
    s = parse({"collection": "c", "questions": [{"id": "j1", "question": "Revenue?", "judged": True,
                                                  "context": {"metric": "revenue", "cik": "1"}}]})
    assert s.questions[0].context == {"metric": "revenue", "cik": "1"}


def test_an_answer_to_a_judged_question_scores_as_answered():
    row = score(judged(), {"answer": "Margins widened by two points."})
    assert row["correct"] and row["score"] == 1.0 and row["judged"]


def test_a_decline_on_a_judged_question_is_a_false_abstention():
    row = score(judged(), {"answer": "", "abstained": True})
    assert not row["correct"] and row["false_abstention"]


def test_a_forbidden_spelling_fails_a_judged_question():
    row = score(judged(must_not=["Jane Doe"]), {"answer": "Jane Doe asked about margins."})
    assert not row["correct"] and row["forbidden"] == ["Jane Doe"]


def test_an_error_fails_a_judged_question_without_counting_as_an_abstention():
    row = score(judged(), {"error": "timeout", "abstained": True})
    assert not row["correct"] and not row["false_abstention"]


def test_the_summary_counts_judged_questions_apart():
    rows = [score(judged(), {"answer": "Up."}), score(Question(id="q", question="?", must=[["x"]]), {"answer": "x"})]
    out = summarise(rows)
    assert out["judged"]["questions"] == 1 and out["all"]["questions"] == 2


def test_the_summary_reports_grades_beside_the_score_never_in_it():
    row = score(judged(), {"answer": "Up."})
    row["grade"] = {"verdict": "fail"}
    out = summarise([row])
    assert out["graded"] == {"fail": 1} and out["all"]["correct"] == 1


def test_a_name_is_found_only_as_a_whole_name():
    assert position("Asked by Ann Lee.", ["Ann Lee"]) is not None
    assert position("Asked by Joann Leeds.", ["Ann Lee"]) is None
