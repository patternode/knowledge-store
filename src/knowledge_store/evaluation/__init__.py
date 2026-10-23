"""BC-007 Evaluation: question sets, runs and scores, without a model as judge in the score.

This module is the context's contract: other contexts import only the names below.
"""

from knowledge_store.kernel.contract import lazy

_EXPORTS: dict[str, str] = {
    "Answerer": "ports",
    "DeepEvalGrader": "adapters.deepeval_grader",
    "DeepEvalRunner": "adapters.deepeval_runner",
    "DirRunStore": "adapters.run_store",
    "EvalSet": "domain.sets",
    "Gate": "domain.compare",
    "Grader": "ports",
    "HhemVerifier": "adapters.verifiers",
    "HttpAnswerer": "adapters.answerers",
    "InProcessAnswerer": "adapters.answerers",
    "KINDS": "domain.sets",
    "LakeRunStore": "adapters.run_store",
    "LexicalVerifier": "adapters.verifiers",
    "Question": "domain.sets",
    "Rules": "domain.compare",
    "RunStore": "ports",
    "Runner": "ports",
    "TruthSource": "ports",
    "compare": "domain.compare",
    "declined": "domain.score",
    "gate": "slices.gate",
    "load_set": "adapters.set_files",
    "matches": "domain.numeric",
    "parse": "domain.sets",
    "position": "domain.score",
    "report": "adapters.report",
    "run": "slices.run_set",
    "score": "domain.score",
    "summarise": "domain.score",
}

__getattr__, __dir__ = lazy(__name__, _EXPORTS)
