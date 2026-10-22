"""What the DeepEval runner and grader share: DeepEval loaded so that nothing leaves the account,
and a question with its reply as a DeepEval test case.

DeepEval sends usage telemetry and, when a Confident AI key is set, uploads every test run. Both
are off here unless the evaluator turns them on: telemetry is opted out before DeepEval is first
imported, a .env file in the working directory is not read, and the runner refuses to run while
a Confident AI key is set unless it was asked to upload. The `evals` extra installs DeepEval,
pinned to DEEPEVAL_VERSION because its metrics' prompts change between releases.
"""

from __future__ import annotations

import os

DEEPEVAL_VERSION = "4.3.1"


def load(cache_dir: str | None = None):
    """DeepEval, imported with telemetry off. cache_dir is where it keeps its run files (it reads
    the folder once, at its first import)."""
    os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "1")
    os.environ.setdefault("DEEPEVAL_DISABLE_DOTENV", "1")
    if cache_dir:
        os.environ.setdefault("DEEPEVAL_CACHE_FOLDER", cache_dir)
    import deepeval
    return deepeval


def uploads() -> bool:
    """Whether a DeepEval run would be sent to Confident AI."""
    load()
    from deepeval.confident.api import is_confident
    return is_confident()


def passages(result: dict) -> list[str]:
    """The text of every passage the reply cites."""
    return [str(s["text"]) for s in result.get("sources") or [] if s.get("text")]


def answer_facts(question) -> list[str]:
    """The facts a right answer states, when the set gives them as sentences (context.answer_facts)."""
    return [str(f) for f in (question.context or {}).get("answer_facts") or []]


def test_case(question, result: dict):
    load()
    from deepeval.test_case import LLMTestCase
    return LLMTestCase(name=question.id, input=question.question,
                       actual_output=result.get("answer") or result.get("error") or "",
                       expected_output=question.expected or None, context=answer_facts(question) or None,
                       retrieval_context=passages(result) or None,
                       metadata={"kind": question.kind, "answerable": question.answerable})
