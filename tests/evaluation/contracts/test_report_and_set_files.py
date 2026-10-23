"""The two remaining adapters: a run as Markdown, and a set read from a YAML file."""

from __future__ import annotations

import pytest

from knowledge_store.evaluation import Question, load_set, report
from knowledge_store.evaluation.adapters.set_files import load
from knowledge_store.evaluation.domain.compare import Gate
from knowledge_store.evaluation.domain.score import score, summarise


def out_of(rows, **extra):
    return {"set": "space", "collection": "missions", "when": "2026-10-20T09:30:00+00:00", "rows": rows,
            "summary": summarise(rows), "tokens": {"inputTokens": 12, "outputTokens": 3}, **extra}


def scored(qid, text, **kw):
    return score(Question(id=qid, question="?", must=[["Atlas V"]], **kw), {"answer": text})


def test_the_report_names_the_set_and_the_measures():
    text = report(out_of([scored("a", "Atlas V"), scored("b", "no")]))
    assert text.startswith("# Evaluation: space (missions)") and "| Correct | 1 of 2 (0.5; 95% interval " in text
    assert "| Tokens (input, output) | 12, 3 |" in text and text.endswith("\n")


def test_the_report_lists_every_question_with_what_was_missing():
    text = report(out_of([scored("a", "Atlas V"), scored("b", "no")]))
    assert "| a | lookup | yes |" in text and "| b | lookup | no | 0.0 |" in text and "Atlas V |" in text


def test_the_report_shows_unsupported_claims_only_when_verified():
    assert "Unsupported claims" not in report(out_of([scored("a", "Atlas V")]))
    row = score(Question(id="a", question="?", must=[["Atlas V"]]), {"answer": "Atlas V", "claims": [{}]}, [{"supported": False}])
    text = report(out_of([row]))
    assert "| Unsupported claims: rejected by the claim verifier | 1 of 1 |" in text and "| 1 |" in text


def test_the_report_shows_the_gate():
    assert "Passed." in report(out_of([scored("a", "Atlas V")]), Gate(passed=True, fixed=["a"]))
    text = report(out_of([scored("a", "no")]), Gate(passed=False, failures=["accuracy fell by 1.000"]))
    assert "## Release gate" in text and "Failed:" in text and "- accuracy fell by 1.000" in text


def test_the_report_names_fixed_questions():
    assert "Now right, wrong in the baseline: a" in report(out_of([scored("a", "Atlas V")]), Gate(passed=True, fixed=["a"]))


def test_the_report_says_why_a_row_failed():
    forbidden = scored("f", "Atlas V or Delta", must_not=["Delta"])
    false_answer = score(Question(id="u", question="?", kind="unanswerable", answerable=False), {"answer": "It was Kent."})
    truth = {**scored("t", "Atlas V"), "correct": False, "truth": {"canary": {"ok": False, "detail": "leak"}}}
    errored = {**scored("e", ""), "error": "RuntimeError: model down"}
    text = report(out_of([forbidden, false_answer, truth, errored]))
    assert "(said Delta)" in text and "false answer" in text and "truth: canary (leak)" in text
    assert "error: RuntimeError: model down" in text


def test_the_report_counts_paraphrase_families():
    rows = [scored("a", "Atlas V", family="j"), scored("b", "Atlas V", family="j")]
    assert "| Paraphrase families answered alike | 1.0 of 1 |" in report(out_of(rows))


def test_the_report_has_a_line_per_kind():
    rows = [scored("a", "Atlas V"), score(Question(id="l", question="?", kind="list", must=[["x"]]), {"answer": "x"})]
    text = report(out_of(rows))
    assert "| lookup | 1 | 1 |" in text and "| list | 1 | 1 |" in text


def test_a_set_file_loads_under_its_file_name(tmp_path):
    pytest.importorskip("yaml")
    p = tmp_path / "tiny.yaml"
    p.write_text("collection: c\nquestions:\n- {id: a, question: '?', must: [x]}\n", encoding="utf-8")
    assert load(p).name == "tiny" and load_set(p).questions[0].must == [["x"]]


def test_a_set_file_that_is_not_a_set_is_refused(tmp_path):
    pytest.importorskip("yaml")
    p = tmp_path / "bad.yaml"
    p.write_text("collection: c\nquestions:\n- {id: a, question: '?'}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_set(p)


def test_the_report_shows_the_grader_beside_the_score_when_one_ran():
    assert "## Grader" not in report(out_of([scored("a", "Atlas V")]))
    rows = [{**scored("a", "Atlas V"), "grade": {"verdict": "pass"}}, {**scored("b", "no"), "grade": {"verdict": "fail"}}]
    text = report(out_of(rows))
    assert "## Grader" in text and "| pass | 1 |" in text and "| fail | 1 |" in text
    assert "| Missing or forbidden | Grade |" in text and text.count("|---") >= 9
    assert "| b | lookup | no | 0.0 |" in text and "| fail |\n" in text
