"""DeepEval as the Runner: the same questions and the same scores, recorded as a DeepEval test run.

Every question is asked and scored in order, as the plain loop does, so a token budget and one
failed question behave alike. The rows are then handed to DeepEval's evaluate() as metrics that
read them back: the deterministic score, and, when a grader ran, each of its metrics. No model is
called here; the grader's calls were made when the question was scored.

The test run is written under results_dir as test_run_<time>.json, beside DeepEval's own files
(.deepeval/). A run is sent to Confident AI only with upload=True; while a Confident AI key is set
and upload is False, the runner refuses to start rather than send it.
"""

from __future__ import annotations

import logging
from pathlib import Path

from knowledge_store.evaluation.adapters.deepeval_cases import load, test_case, uploads

log = logging.getLogger("evaluation")


def _metric(name: str, value_of, threshold: float):
    """A DeepEval metric that reports a value already in each row: value_of(row) gives
    (score, passed, reason), or None when the row has nothing for this metric."""
    load()
    from deepeval.errors import MissingTestCaseParamsError
    from deepeval.metrics import BaseMetric

    class RowMetric(BaseMetric):
        def __init__(self, rows: dict[str, dict]):
            self.rows, self.threshold = rows, threshold
            self.async_mode, self.include_reason, self.strict_mode = False, True, False
            self.evaluation_model = None

        def measure(self, case, *args, **kwargs):
            got = value_of(self.rows.get(case.name) or {})
            if got is None:
                raise MissingTestCaseParamsError(f"{name}: nothing for {case.name}")
            self.score, self.success, self.reason = got
            return self.score

        async def a_measure(self, case, *args, **kwargs):
            return self.measure(case)

        def is_successful(self) -> bool:
            return bool(self.success)

        @property
        def __name__(self):
            return name

    return RowMetric


def _score(row: dict):
    why = [f"missing {', '.join(row['missing'])}" if row.get("missing") else "",
           f"states {', '.join(row['forbidden'])}" if row.get("forbidden") else "",
           "false answer" if row.get("false_answer") else "", "false abstention" if row.get("false_abstention") else "",
           f"{row['unsupported']} unsupported claim(s)" if row.get("unsupported") else "", row.get("error") or ""]
    return float(row.get("score") or 0.0), bool(row.get("correct")), "; ".join(w for w in why if w) or "correct"


def _graded(metric: str):
    def value_of(row: dict):
        m = ((row.get("grade") or {}).get("metrics") or {}).get(metric)
        return None if not m or m.get("score") is None else (float(m["score"]), bool(m["passed"]), m.get("reason") or "")
    return value_of


class DeepEvalRunner:
    def __init__(self, results_dir: str, *, identifier: str | None = None, upload: bool = False):
        self.results_dir, self.identifier, self.upload = str(results_dir), identifier, upload
        load(str(Path(results_dir) / ".deepeval"))

    def __call__(self, questions, ask, score_one):
        if uploads() and not self.upload:
            raise RuntimeError("a Confident AI key is set, so DeepEval would upload the questions and answers. "
                               "Unset CONFIDENT_API_KEY, or ask for the upload.")
        triples = [(q, res, score_one(q, res)) for q in questions for res in [ask(q)]]
        if triples:
            try:
                self.record(triples)
            except Exception as e:  # the scores stand without DeepEval's record of them
                log.warning("DeepEval did not record the run: %s: %s", type(e).__name__, e)
        return triples

    def record(self, triples):
        from deepeval import evaluate
        from deepeval.evaluate.configs import AsyncConfig, CacheConfig, DisplayConfig, ErrorConfig

        rows = {q.id: row for q, _, row in triples}
        graded = sorted({k for row in rows.values() for k in ((row.get("grade") or {}).get("metrics") or {})})
        metrics = [_metric("Knowledge Store score", _score, 1.0)(rows)]
        metrics += [_metric(f"grade: {k}", _graded(k), 0.5)(rows) for k in graded]
        Path(self.results_dir).mkdir(parents=True, exist_ok=True)
        return evaluate([test_case(q, res) for q, res, _ in triples], metrics, identifier=self.identifier,
                        async_config=AsyncConfig(run_async=False),
                        display_config=DisplayConfig(print_results=False, show_indicator=False,
                                                     results_folder=self.results_dir, inspect_after_run=False),
                        error_config=ErrorConfig(skip_on_missing_params=True),
                        cache_config=CacheConfig(write_cache=False))
