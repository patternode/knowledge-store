"""The evaluation framework: the example set loads, answers are scored without a model, and a run
writes its report. The agent is replaced by prepared answers."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("yaml")

from knowledge_store.evals import run, score  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SET = ROOT / "examples/evals/space-missions.yaml"


def answer(text, sources=(), abstained=False, proposed=1, shown=1):
    return {"answer": text, "abstained": abstained, "sources": [{"name": s, "title": s} for s in sources],
            "grounding": {"claims_proposed": proposed, "claims_shown": shown}}


def q(**kw):
    return score.Question(**{"id": "x", "question": "?", "must": [["Atlas V 551", "Atlas V"]], **kw})


def test_the_example_set_loads():
    ev = score.load(SET)
    assert ev.collection == "missions" and len(ev.questions) == 22
    assert sum(not x.answerable for x in ev.questions) == 3
    assert {x.kind for x in ev.questions} == set(score.KINDS)


def test_facts_spellings_and_word_boundaries():
    assert score.score(q(), answer("Juno launched on an Atlas V rocket. [1]"))["correct"]
    assert not score.score(q(), answer("an Atlas Vx"))["correct"]


def test_must_not_and_order():
    r = score.score(q(must=[["10", "ten"]], must_not=["11"]), answer("Ten missions, or 11 with Ingenuity."))
    assert r["score"] == 0.0 and r["forbidden"] == ["11"]
    cmp = q(kind="comparison", must=[["Voyager 2"]], first=["Voyager 2", "Voyager 1"])
    assert score.score(cmp, answer("Voyager 2 launched before Voyager 1."))["correct"]
    assert not score.score(cmp, answer("Voyager 1 launched after Voyager 2."))["correct"]


def test_unanswerable_is_correct_only_when_the_agent_abstains():
    u = q(kind="unanswerable", answerable=False, must=[])
    assert score.score(u, answer("I can't answer that from the sources.", abstained=True))["correct"]
    assert not score.score(u, answer("It cost a billion dollars."))["correct"]


def test_grounded_and_source_hit():
    r = score.score(q(sources=["outer-planets/juno.json"]), answer("Atlas V 551", ["juno.json"], proposed=4, shown=3))
    assert r["grounded"] == 0.75 and r["source_hit"] is True
    assert score.score(q(sources=["outer-planets/juno.json"]), answer("Atlas V", ["dawn.md"]))["source_hit"] is False


def test_a_bad_set_is_refused(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("collection: c\nquestions:\n- {id: a, question: '?', kind: lookup}\n")
    with pytest.raises(ValueError, match="needs at least one fact"):
        score.load(bad)
    bad.write_text("collection: c\nquestions:\n- {id: a, question: '?', kind: unanswerable}\n")
    with pytest.raises(ValueError, match="answerable: false"):
        score.load(bad)


def test_a_run_scores_reports_and_survives_a_failing_question(tmp_path):
    ev = score.load(SET)
    unans = [x for x in ev.questions if not x.answerable][:1]
    ev.questions = ev.questions[:2] + unans
    replies = {"q01": answer("Juno launched on an Atlas V 551. [1]", ["juno.json"]),
               unans[0].id: answer("I can't answer that from the sources in this collection.", abstained=True, proposed=0, shown=0)}

    def ask(question):
        if question.id not in replies:
            raise RuntimeError("model unavailable")
        return replies[question.id]
    out = run.run(ev, ask, progress=lambda *_: None)
    s = out["summary"]["all"]
    assert s["questions"] == 3 and s["correct"] == 2 and s["errors"] == 1
    text = run.report(out)
    assert "| Correct | 2 of 3" in text and "| q02 | lookup | no |" in text and "error: RuntimeError" in text


def test_nothing_runs_without_yes(capsys):
    assert run.main([str(SET), "--lake", "unused"]) == 2
    assert "--yes" in capsys.readouterr().out
