"""Answering's ports: where the checks around an answer vary.

QuestionScreen decides whether a question may reach the agent at all. ClaimVerifier decides
whether a claim follows from the passage, cell or figure it cites, after the deterministic quote
and value checks have passed. The Bedrock Guardrail implements both
(answering.adapters.bedrock_guardrail); the Evaluation context uses the same ClaimVerifier, so
an evaluation measures what production enforces (patternode-architecture ADR-048).
"""

from __future__ import annotations

from typing import Protocol


class QuestionScreen(Protocol):
    def question(self, text: str) -> str | None:
        """None if the question may go to the agent, else the message to show instead."""


class ClaimVerifier(Protocol):
    def grounded(self, question: str, claim: str, sources: list[str]) -> tuple[bool, float | None]:
        """Whether the claim follows from its sources, and the score where the verifier has one."""


class Guard(QuestionScreen, ClaimVerifier, Protocol):
    """Both checks, as one object: what the agent loop is given."""
