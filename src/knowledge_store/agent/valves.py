"""Valves: the limits around every question, in one place.

    MAX_QUESTION_CHARS    2000  a longer question is refused before any model call
    MAX_HISTORY_TURNS     6     earlier turns of the conversation passed to the agent
    MAX_TOOL_CALLS        16    tool calls per question; past it a tool call is refused and the
                                agent is told to answer from what it has read
    MAX_MODEL_CALLS       14    model calls per question, the hard stop
    MAX_OUTPUT_TOKENS     4000  per model call
    GROUNDING_REPAIRS     1     times the agent is shown its failed citations and asked again

and, with GUARDRAIL_ID set, a Bedrock Guardrail applied twice (ApplyGuardrail, outside the model
call so that passages read by tools are never screened as if they were the person's input):

    the question          prompt attacks, denied topics and content filters, before the agent runs
    each claim            contextual grounding against the passages it cites, after the quote check

The chat API adds its own: a daily question quota per person, and the Lambda's reserved
concurrency. Each number is an environment variable, set from Terraform.
"""

from __future__ import annotations

import os


def limit(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


MAX_QUESTION_CHARS = limit("MAX_QUESTION_CHARS", 2000)
MAX_HISTORY_TURNS = limit("MAX_HISTORY_TURNS", 6)
MAX_TOOL_CALLS = limit("MAX_TOOL_CALLS", 16)
MAX_MODEL_CALLS = limit("MAX_MODEL_CALLS", 14)
MAX_OUTPUT_TOKENS = limit("MAX_OUTPUT_TOKENS", 4000)
GROUNDING_REPAIRS = limit("GROUNDING_REPAIRS", 1)

TOOL_BUDGET_SPENT = "Tool budget for this question is spent. Answer now from the passages you have read."


class Guardrail:
    """ApplyGuardrail on the question (INPUT) and on each claim (OUTPUT, contextual grounding)."""

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
        contextual grounding check. A guardrail without that check passes every claim."""
        r = self._apply("OUTPUT", [{"text": {"text": "\n\n".join(sources)[:100000], "qualifiers": ["grounding_source"]}},
                                   {"text": {"text": question, "qualifiers": ["query"]}},
                                   {"text": {"text": claim, "qualifiers": ["guard_content"]}}])
        for a in r.get("assessments") or []:
            for f in (a.get("contextualGroundingPolicy") or {}).get("filters") or []:
                if f.get("type") == "GROUNDING":
                    return f.get("action") != "BLOCKED", f.get("score")
        return True, None
