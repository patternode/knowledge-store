"""The Grader port: DeepEval's judgement of an answer, beside the score. Run offline on a judge
that answers DeepEval's prompts from a script, keyed by the reply schema DeepEval asks for."""

from __future__ import annotations

import json

import pytest

from knowledge_store.evaluation import Question

pytest.importorskip("deepeval")

from knowledge_store.evaluation.adapters.deepeval_grader import DeepEvalGrader, json_object, judge  # noqa: E402

Q = Question(id="a", question="Which rocket?", expected="Atlas V", must=[["Atlas V"]])
SOURCES = [{"text": "The probe launched on an Atlas V."}]


class ScriptedClient:
    """A Converse client whose reply depends on the JSON schema DeepEval asks for."""

    def __init__(self, score: int = 9, supported: str = "yes"):
        self.calls, self.score, self.supported = [], score, supported

    def replies(self, title):
        return {
            "ReasonScore": {"reason": "states the expected answer", "score": self.score},
            "Truths": {"truths": ["The probe launched on an Atlas V."]},
            "Claims": {"claims": ["The rocket was an Atlas V."]},
            "Verdicts": {"verdicts": [{"verdict": self.supported, "reason": None if self.supported == "yes" else "not in the passage"}]},
            "FaithfulnessScoreReason": {"reason": "every claim is supported"},
        }[title]

    def converse(self, modelId, messages, inferenceConfig):
        prompt = messages[0]["content"][0]["text"]
        title = json.loads(prompt[prompt.rfind("JSON schema:\n") + 13:])["title"]
        self.calls.append((modelId, title, inferenceConfig))
        text = "```json\n" + json.dumps(self.replies(title)) + "\n```"
        return {"output": {"message": {"content": [{"text": text}]}}}


def grader(client, **kw):
    return DeepEvalGrader(model=judge("judge-model", client), **kw)


def test_a_correct_supported_answer_passes():
    client = ScriptedClient()
    g = grader(client).grade(Q, {"answer": "Atlas V", "sources": SOURCES})
    assert g["verdict"] == "pass" and set(g["metrics"]) == {"correctness", "faithfulness"}
    assert g["metrics"]["correctness"]["score"] == pytest.approx(0.9)
    assert g["model"] == "judge-model"
    assert {m for m, _, _ in client.calls} == {"judge-model"}
    assert all(cfg["temperature"] == 0 for _, _, cfg in client.calls)


def test_a_wrong_unsupported_answer_fails():
    g = grader(ScriptedClient(score=1, supported="no")).grade(Q, {"answer": "Delta II", "sources": SOURCES})
    assert g["verdict"] == "fail" and not any(m["passed"] for m in g["metrics"].values())


def test_one_metric_passing_is_partial():
    g = grader(ScriptedClient(score=9, supported="no")).grade(Q, {"answer": "Atlas V", "sources": SOURCES})
    assert g["verdict"] == "partial"


def test_nothing_to_judge_is_skipped_without_a_model_call():
    client = ScriptedClient()
    q = Question(id="u", question="?", must=[], answerable=False)
    g = grader(client).grade(q, {"answer": "", "abstained": True})
    assert g["verdict"] == "skipped" and client.calls == []


def test_faithfulness_can_be_left_out():
    g = grader(ScriptedClient(), faithfulness=False).grade(Q, {"answer": "Atlas V", "sources": SOURCES})
    assert set(g["metrics"]) == {"correctness"}


def test_a_metric_that_fails_to_run_is_reported_not_raised():
    class Broken(ScriptedClient):
        def replies(self, title):
            return {} if title == "Truths" else super().replies(title)

    g = grader(Broken()).grade(Q, {"answer": "Atlas V", "sources": SOURCES})
    assert g["metrics"]["correctness"]["passed"] and g["metrics"]["faithfulness"]["score"] is None
    assert g["verdict"] == "partial"


def test_the_grader_needs_a_judge():
    with pytest.raises(ValueError):
        DeepEvalGrader()


def test_json_object_takes_the_object_out_of_a_reply():
    assert json.loads(json_object('Here it is:\n```json\n{"a": {"b": 1}}\n```')) == {"a": {"b": 1}}
    with pytest.raises(ValueError):
        json_object("no object")


def test_completeness_is_judged_over_the_answer_facts_alone():
    client = ScriptedClient(score=5)
    q = Question(id="f", question="Which rocket?", expected="Atlas V", judged=True,
                 context={"answer_facts": ["The rocket was an Atlas V.", "It launched in 2011."]})
    g = grader(client, faithfulness=False).grade(q, {"answer": "Atlas V", "sources": SOURCES})
    assert set(g["metrics"]) == {"correctness", "completeness"}
    assert g["metrics"]["completeness"]["score"] == pytest.approx(0.5) and g["metrics"]["completeness"]["passed"]
    assert all(title == "ReasonScore" for _, title, _ in client.calls)


def test_no_answer_facts_means_no_completeness_metric():
    g = grader(ScriptedClient(), faithfulness=False).grade(Q, {"answer": "Atlas V", "sources": SOURCES})
    assert set(g["metrics"]) == {"correctness"}


def test_the_judge_makes_the_platform_client_on_first_use_and_answers_asynchronously(monkeypatch):
    import asyncio
    import knowledge_store.platform_services as ps

    class Plain:
        def converse(self, modelId, messages, inferenceConfig):
            return {"output": {"message": {"content": [{"text": f"ok {modelId}"}]}}}

    monkeypatch.setattr(ps, "runtime_client", lambda: Plain(), raising=False)
    j = judge("judge-model")
    assert j.generate("hello") == "ok judge-model"
    assert asyncio.run(j.a_generate("hello")) == "ok judge-model"
