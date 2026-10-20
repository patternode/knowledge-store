"""A Bedrock Guardrail as Answering's question screen and claim verifier.

ApplyGuardrail runs twice, outside the model call, so that passages and cells read by tools are
never screened as if they were the person's input: on the question (INPUT: prompt attacks,
denied topics, content filters) before the agent runs, and on each claim (OUTPUT: contextual
grounding against the passage, cell or figure it cites) after the quote or value check. The
guardrail itself is configured outside this code; this adapter only calls it.
"""

from __future__ import annotations

import os


class Guardrail:
    """ApplyGuardrail on the question (INPUT) and on each claim (OUTPUT, contextual grounding).
    Implements answering.ports.QuestionScreen and answering.ports.ClaimVerifier."""

    def __init__(self, guardrail_id: str, version: str = "DRAFT", client=None):
        import boto3
        self.id, self.version = guardrail_id, version
        self.client = client or boto3.client("bedrock-runtime")

    @classmethod
    def from_env(cls) -> "Guardrail | None":
        gid = os.environ.get("GUARDRAIL_ID")
        return cls(gid, os.environ.get("GUARDRAIL_VERSION", "DRAFT")) if gid else None

    def _apply(self, source: str, content: list[dict]) -> dict:
        return self.client.apply_guardrail(guardrailIdentifier=self.id, guardrailVersion=self.version,
                                           source=source, content=content)

    def question(self, text: str) -> str | None:
        """None if the question may go to the agent, else the guardrail's message."""
        r = self._apply("INPUT", [{"text": {"text": text}}])
        if r.get("action") == "GUARDRAIL_INTERVENED":
            outs = r.get("outputs") or []
            return outs[0]["text"] if outs else "That question can't be answered here."
        return None

    def grounded(self, question: str, claim: str, sources: list[str]) -> tuple[bool, float | None]:
        """Whether the claim is grounded in its sources, and the score, by the guardrail's
        contextual grounding check. sources are the passage text, or `column: value` for a
        cell, or the figure for a metric. A guardrail without that check passes every claim."""
        r = self._apply("OUTPUT", [{"text": {"text": "\n\n".join(sources)[:100000], "qualifiers": ["grounding_source"]}},
                                   {"text": {"text": question, "qualifiers": ["query"]}},
                                   {"text": {"text": claim, "qualifiers": ["guard_content"]}}])
        for a in r.get("assessments") or []:
            for f in (a.get("contextualGroundingPolicy") or {}).get("filters") or []:
                if f.get("type") == "GROUNDING":
                    return f.get("action") != "BLOCKED", f.get("score")
        return True, None
