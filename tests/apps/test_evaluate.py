"""The evaluation command (apps/evaluate.py) end to end: a set, a fake Answerer behind the
InProcessAnswerer's name, a run folder, the gate; and every refusal before money is spent."""

from __future__ import annotations

import json

import pytest

pytest.importorskip("yaml")

from knowledge_store.apps import evaluate  # noqa: E402
from knowledge_store.evaluation import DirRunStore, LakeRunStore, LexicalVerifier  # noqa: E402

SET = """collection: missions
name: tiny
questions:
- {id: q1, question: 'Which rocket launched Juno?', must: [[Atlas V]]}
- {id: q2, question: 'Who built it?', must: [[Lockheed]]}
"""


@pytest.fixture
def set_file(tmp_path):
    p = tmp_path / "tiny.yaml"
    p.write_text(SET, encoding="utf-8")
    return str(p)


@pytest.fixture
def answers(monkeypatch):
    replies = {"Which rocket launched Juno?": "Juno launched on an Atlas V.", "Who built it?": "Lockheed Martin."}

    class Fake:
        made = []

        def __init__(self, *args):
            Fake.made.append(args)

        def __call__(self, q):
            return {"answer": replies[q.question], "abstained": False, "usage": {"inputTokens": 5, "outputTokens": 1}}
    monkeypatch.setattr(evaluate, "InProcessAnswerer", Fake)
    monkeypatch.setattr(evaluate, "HttpAnswerer", Fake)
    for v in ("LAKE_URI", "AGENT_MODEL_ID", "KS_TOKEN"):
        monkeypatch.delenv(v, raising=False)
    return replies, Fake


def test_a_run_answers_scores_and_writes_its_report(set_file, answers, tmp_path, capsys):
    out = tmp_path / "eval"
    assert evaluate.main([set_file, "--lake", "lake", "--model", "m", "--out", str(out), "--yes"]) == 0
    printed = capsys.readouterr().out
    assert "| Correct | 2 of 2" in printed and "written to" in printed
    run_dir = next(p for p in out.iterdir() if p.name.startswith("tiny-"))
    assert json.loads((run_dir / "results.json").read_text())["summary"]["all"]["correct"] == 2
    assert answers[1].made == [("lake", "missions", "m")]


def test_the_gate_keeps_a_first_baseline_and_fails_a_regression(set_file, answers, tmp_path, capsys):
    out = str(tmp_path / "eval")
    args = [set_file, "--lake", "lake", "--model", "m", "--out", out, "--yes", "--gate"]
    assert evaluate.main(args + ["--keep-baseline"]) == 0
    answers[0]["Who built it?"] = "Nobody knows."
    assert evaluate.main(args) == 3
    assert "right in the baseline are wrong now: q2" in capsys.readouterr().out


def test_only_runs_the_named_questions(set_file, answers, tmp_path, capsys):
    assert evaluate.main([set_file, "--lake", "l", "--model", "m", "--out", str(tmp_path), "--only", "q2", "--yes"]) == 0
    assert "| Correct | 1 of 1" in capsys.readouterr().out


def test_a_question_that_fails_makes_the_exit_code_one(set_file, answers, tmp_path, monkeypatch):
    del answers[0]["Who built it?"]
    assert evaluate.main([set_file, "--lake", "l", "--model", "m", "--out", str(tmp_path), "--yes"]) == 1


def test_against_the_api_it_asks_as_the_tokens_person(set_file, answers, tmp_path, monkeypatch):
    monkeypatch.setenv("KS_TOKEN", "tok")
    assert evaluate.main([set_file, "--api", "https://ks.example", "--out", str(tmp_path), "--yes"]) == 0
    assert answers[1].made == [("https://ks.example", "tok", "missions")]


def test_nothing_runs_without_yes_and_the_estimate_is_printed(set_file, answers, capsys):
    assert evaluate.main([set_file, "--lake", "l", "--model", "m"]) == 2
    assert "2 questions" in capsys.readouterr().out and answers[1].made == []


@pytest.mark.parametrize("args,why", [([], "give --lake"), (["--lake", "l"], "give --model"),
                                      (["--api", "https://x"], "set KS_TOKEN")])
def test_it_refuses_without_what_it_needs(set_file, answers, capsys, args, why):
    assert evaluate.main([set_file, *args, "--yes"]) == 2
    assert why in capsys.readouterr().out and answers[1].made == []


def test_verifiers_by_name(monkeypatch):
    assert evaluate.verifier_for("none") is None
    assert isinstance(evaluate.verifier_for("lexical"), LexicalVerifier)
    import knowledge_store.answering as answering
    monkeypatch.setattr(answering.Guardrail, "from_env", classmethod(lambda cls: None))
    with pytest.raises(SystemExit, match="GUARDRAIL_ID"):
        evaluate.verifier_for("guardrail")


def test_stores_by_destination(tmp_path, monkeypatch):
    assert isinstance(evaluate.store_for(str(tmp_path)), DirRunStore)
    import knowledge_store.platform_services as ps
    monkeypatch.setattr(ps, "store_from_uri", lambda uri: ("store", uri), raising=False)
    s = evaluate.store_for("s3://bucket")
    assert isinstance(s, LakeRunStore) and s.store == ("store", "s3://bucket")


def test_another_systems_answers_are_scored_from_a_file(set_file, answers, tmp_path, capsys):
    rows = [{"question_id": "q1", "answer": "Juno launched on an Atlas V.", "document_ids": ["dsid_j"]},
            {"question_id": "q2", "answer": "Lockheed Martin built it.", "document_ids": []}]
    (tmp_path / "onyx.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    (tmp_path / "index.json").write_text(json.dumps({"dsid_j": "missions/juno.json"}), encoding="utf-8")
    assert evaluate.main([set_file, "--answers", str(tmp_path / "onyx.jsonl"), "--answers-index",
                          str(tmp_path / "index.json"), "--documents", str(tmp_path), "--out",
                          str(tmp_path / "out")]) == 2
    assert "about 0.00 USD" in capsys.readouterr().out
    code = evaluate.main([set_file, "--answers", str(tmp_path / "onyx.jsonl"), "--answers-index",
                          str(tmp_path / "index.json"), "--out", str(tmp_path / "out"), "--yes"])
    assert code == 0 and answers[1].made == []
    run = json.loads(next((tmp_path / "out").rglob("results.json")).read_text(encoding="utf-8"))
    assert run["summary"]["all"]["correct"] == 2
    assert run["results"][0]["result"]["sources"][0]["name"] == "missions/juno.json"


def test_the_grader_needs_a_judge_model_when_no_answering_model_is_named(set_file, answers, capsys, monkeypatch):
    monkeypatch.setenv("KS_TOKEN", "tok")
    assert evaluate.main([set_file, "--api", "https://x", "--grader", "deepeval", "--yes"]) == 2
    assert "give --judge-model" in capsys.readouterr().out and answers[1].made == []


def test_the_deepeval_runner_and_grader_are_wired_in(set_file, answers, tmp_path, monkeypatch):
    import knowledge_store.evaluation as evaluation
    made = {}

    class Runner:
        def __init__(self, results_dir, *, identifier=None, upload=False):
            made["runner"] = (results_dir, identifier, upload)

        def __call__(self, questions, ask, score_one):
            return [(q, res, score_one(q, res)) for q in questions for res in [ask(q)]]

    class Grader:
        def __init__(self, model_id):
            made["grader"] = model_id

        def grade(self, q, res):
            return {"verdict": "pass", "explanation": "", "metrics": {}, "model": made["grader"]}

    monkeypatch.setattr(evaluation, "DeepEvalRunner", Runner, raising=False)
    monkeypatch.setattr(evaluation, "DeepEvalGrader", Grader, raising=False)
    out = tmp_path / "eval"
    assert evaluate.main([set_file, "--lake", "l", "--model", "m", "--out", str(out), "--runner", "deepeval",
                          "--grader", "deepeval", "--judge-model", "judge", "--yes"]) == 0
    assert made == {"runner": (str(out / "deepeval"), "tiny", False), "grader": "judge"}
    run_dir = next(p for p in out.iterdir() if p.name.startswith("tiny-"))
    rows = json.loads((run_dir / "results.json").read_text())["rows"]
    assert all(r["grade"]["verdict"] == "pass" for r in rows)
