"""Inspect AI as the Runner: the same questions and the same scores, with Inspect's log and viewer.

Inspect needs a model to run a task; the solver here never calls it (the system under test is
the Answerer), so the task runs on Inspect's mock model and needs no network of its own. The
`evals` extra installs Inspect, pinned to one version because it changes weekly. View a run's
log with `inspect view --log-dir <dir>`.
"""

from __future__ import annotations

INSPECT_VERSION = "0.3.282"


class InspectRunner:
    def __init__(self, log_dir: str, max_samples: int = 4, epochs: int = 1):
        self.log_dir, self.max_samples, self.epochs = log_dir, max_samples, epochs

    def __call__(self, questions, ask, score_one):
        import asyncio

        from inspect_ai import Task, eval as inspect_eval
        from inspect_ai.dataset import MemoryDataset, Sample
        from inspect_ai.scorer import CORRECT, INCORRECT, Score, accuracy, scorer, stderr
        from inspect_ai.solver import solver

        by_id = {q.id: q for q in questions}
        done: dict[str, tuple] = {}

        @solver
        def ask_system():
            async def solve(state, generate):
                q = by_id[state.metadata["id"]]
                res = await asyncio.to_thread(ask, q)
                state.metadata["result"] = res
                state.output.completion = res.get("answer") or res.get("error") or ""
                return state
            return solve

        @scorer(metrics=[accuracy(), stderr()])
        def deterministic():
            async def score(state, target):
                q = by_id[state.metadata["id"]]
                res = state.metadata.get("result") or {}
                row = score_one(q, res)
                done[q.id] = (q, res, row)
                return Score(value=CORRECT if row["correct"] else INCORRECT, answer=res.get("answer") or "",
                             explanation=", ".join(row.get("missing") or []) or None,
                             metadata={k: row[k] for k in ("score", "grounded", "unsupported", "false_answer") if k in row})
            return score

        task = Task(dataset=MemoryDataset([Sample(id=q.id, input=q.question, metadata={"id": q.id}) for q in questions]),
                    solver=ask_system(), scorer=deterministic(), epochs=self.epochs)
        inspect_eval(task, model="mockllm/model", log_dir=self.log_dir, max_samples=self.max_samples, display="none")
        return [done[q.id] for q in questions if q.id in done]
