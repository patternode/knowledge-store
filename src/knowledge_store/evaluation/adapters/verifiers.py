"""Claim verifiers: does this passage support this claim?

    LexicalVerifier   deterministic and dependency-free: every number and year in the claim is
                      stated in a source, the best-matching source sentence agrees with the claim
                      on negation, and most of the claim's content words appear in the sources. A
                      floor, not a judge of meaning; it runs in tests and offline.
    HhemVerifier      Vectara's HHEM-2.1-Open (Apache-2.0, about 0.1 billion parameters, runs on a
                      CPU), pinned to one revision so its verdicts are reproducible. The `verify`
                      extra installs it. Its threshold is calibrated on hand-labelled claims before
                      it gates a release (patternode-architecture ADR-048).

Answering's Bedrock Guardrail (answering.Guardrail) is a third, behind the same port.
"""

from __future__ import annotations

from knowledge_store.answering import LexicalVerifier  # noqa: F401  (Answering's; re-exported)

HHEM_MODEL = "vectara/hallucination_evaluation_model"
HHEM_REVISION = "de9a5e6ba9ba49531a022dba17e35ffeb2a6fad8"


class HhemVerifier:
    def __init__(self, threshold: float = 0.5, revision: str = HHEM_REVISION, model=None):
        self.threshold = threshold
        if model is None:
            from transformers import AutoModelForSequenceClassification
            model = AutoModelForSequenceClassification.from_pretrained(HHEM_MODEL, trust_remote_code=True, revision=revision)
        self.model = model

    def grounded(self, question: str, claim: str, sources: list[str]) -> tuple[bool, float | None]:
        premise = "\n".join(sources)[:8000]
        score = float(self.model.predict([(premise, claim)])[0])
        return score >= self.threshold, round(score, 3)
