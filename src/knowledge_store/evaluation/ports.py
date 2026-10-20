"""Evaluation's ports (patternode-architecture ADR-048).

    Answerer       the system under test: Knowledge Store's agent in process or over its chat API,
                   or any other system an application points the set at
    TruthSource    independent facts an application supplies (XBRL figures, canary names, a gold
                   set): checks that need data the set file does not hold
    ClaimVerifier  whether a passage supports a claim; Answering's port, shared so that an
                   evaluation measures what production enforces
    Grader         an optional model judge, kept apart from the deterministic score
    RunStore       where runs and baselines are kept
    Runner         what drives the questions: a plain loop, or Inspect AI for its logs and viewer
"""

from __future__ import annotations

from typing import Callable, Protocol

from knowledge_store.answering import ClaimVerifier  # noqa: F401  (re-exported: the shared port)
from knowledge_store.evaluation.domain.sets import Question


class Answerer(Protocol):
    def __call__(self, question: Question) -> dict:
        """The system's reply: answer, abstained, claims, sources, gaps, grounding, usage."""


class TruthSource(Protocol):
    name: str

    def check(self, question: Question, result: dict) -> dict:
        """{"ok": bool | None, "detail": str}: None when this source has nothing to say."""


class Grader(Protocol):
    def grade(self, question: Question, result: dict) -> dict:
        """{"verdict": "pass" | "partial" | "fail", "explanation": str, ...}."""


class RunStore(Protocol):
    def save(self, name: str, run: dict, report: str) -> str: ...
    def baseline(self, set_name: str) -> dict | None: ...
    def keep_as_baseline(self, set_name: str, run: dict) -> None: ...


class Runner(Protocol):
    def __call__(self, questions: list[Question], ask: Callable[[Question], dict],
                 score: Callable[[Question, dict], dict]) -> list[tuple[Question, dict, dict]]:
        """Ask every question and score it: (question, result, row) in order."""
