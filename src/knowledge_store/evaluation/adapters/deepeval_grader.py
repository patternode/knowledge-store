"""DeepEval as the Grader: a model's judgement of each answer, reported beside the score.

Two DeepEval metrics, each run only when the question gives it something to judge:

    correctness    G-Eval against the set's expected answer and, when the set gives them, its
                   answer facts (context.answer_facts): every fact stated, nothing contradicted
    faithfulness   whether the claims in the answer are supported by the passages it cites

The verdict is pass when every metric that ran passed, fail when none did, partial otherwise,
and skipped when neither had anything to judge. ADR-013: the grade never changes the score.

The judge is the platform's model client (platform_services.runtime_client), so its calls go to
Bedrock or the Anthropic API, as every other model call does, and are recorded in the call ledger.
DeepEval's own model clients, which default to OpenAI, are never used.
"""

from __future__ import annotations

import asyncio
import json
import re

from knowledge_store.evaluation.adapters.deepeval_cases import load, test_case

CORRECTNESS_STEPS = [
    "Compare the actual output with the expected output and, when context is given, with each fact listed there.",
    "Penalise heavily any statement in the actual output that contradicts the expected output or a listed fact.",
    "Penalise each listed fact, or each part of the expected output, that the actual output leaves out.",
    "Do not penalise wording, order, or extra detail that contradicts nothing.",
]


def json_object(text: str) -> str:
    """The JSON object in a model's reply, without a code fence or words around it."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError(f"no JSON object in the judge's reply: {text[:200]!r}")
    return text[start:end + 1]


def judge(model_id: str, client=None):
    """A DeepEval model that answers through a Converse client (the platform's by default)."""
    load()
    from deepeval.models import DeepEvalBaseLLM

    class ConverseJudge(DeepEvalBaseLLM):
        def __init__(self):
            self.model_id = model_id
            self.client = client
            super().__init__(model_id)

        def load_model(self):
            return self  # DeepEval calls this on construction; the client is made on the first call

        def _client(self):
            if self.client is None:
                from knowledge_store.platform_services import runtime_client
                self.client = runtime_client()
            return self.client

        def generate(self, prompt: str, schema=None):
            if schema is not None:
                prompt += ("\n\nReply with one JSON object and nothing else, matching this JSON schema:\n"
                           + json.dumps(schema.model_json_schema()))
            resp = self._client().converse(modelId=self.model_id,
                                              messages=[{"role": "user", "content": [{"text": prompt}]}],
                                              inferenceConfig={"maxTokens": 4000, "temperature": 0})
            text = "".join(b.get("text", "") for b in resp["output"]["message"]["content"])
            return text if schema is None else schema.model_validate_json(json_object(text))

        async def a_generate(self, prompt: str, schema=None):
            return await asyncio.to_thread(self.generate, prompt, schema)

        def get_model_name(self) -> str:
            return self.model_id

    return ConverseJudge()


def _reason(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()[:500]


class DeepEvalGrader:
    def __init__(self, model_id: str | None = None, *, model=None, threshold: float = 0.5, faithfulness: bool = True):
        if model is None and not model_id:
            raise ValueError("the grader needs a judge model id")
        self.model = model or judge(model_id)
        self.threshold, self.faithfulness = threshold, faithfulness

    def metrics(self, question, case) -> dict:
        load()
        from deepeval.metrics import FaithfulnessMetric, GEval
        from deepeval.test_case import SingleTurnParams as P
        out = {}
        if question.answerable and case.expected_output:
            params = [P.INPUT, P.ACTUAL_OUTPUT, P.EXPECTED_OUTPUT] + ([P.CONTEXT] if case.context else [])
            out["correctness"] = GEval(name="Correctness", evaluation_steps=CORRECTNESS_STEPS, evaluation_params=params,
                                       model=self.model, threshold=self.threshold, async_mode=False)
        if self.faithfulness and case.retrieval_context and case.actual_output:
            out["faithfulness"] = FaithfulnessMetric(model=self.model, threshold=self.threshold, async_mode=False)
        return out

    def grade(self, question, result: dict) -> dict:
        case = test_case(question, result)
        metrics = self.metrics(question, case)
        if not metrics:
            return {"verdict": "skipped", "explanation": "nothing to judge: no expected answer and no cited passage",
                    "metrics": {}, "model": self.model.get_model_name()}
        scores = {}
        for name, m in metrics.items():
            try:
                m.measure(case)
                scores[name] = {"score": m.score, "passed": bool(m.success), "reason": _reason(m.reason)}
            except Exception as e:  # one metric failing leaves the others' judgement standing
                scores[name] = {"score": None, "passed": False, "reason": f"{type(e).__name__}: {_reason(str(e))}"}
        passed = [s["passed"] for s in scores.values()]
        verdict = "pass" if all(passed) else "fail" if not any(passed) else "partial"
        return {"verdict": verdict, "explanation": "; ".join(f"{k}: {v['reason']}" for k, v in scores.items()),
                "metrics": scores, "model": self.model.get_model_name()}
