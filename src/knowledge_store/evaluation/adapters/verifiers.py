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

import re

from knowledge_store.evaluation.domain import numeric

STOP = set("""a an and are as at be been by for from has have in into is it its of on or that the their this to was were
which with will would its they them he she his her we our you your than then there these those also about""".split())
HHEM_MODEL = "vectara/hallucination_evaluation_model"
HHEM_REVISION = "de9a5e6ba9ba49531a022dba17e35ffeb2a6fad8"


YEAR = re.compile(r"\b(?:19|20)\d\d\b")
SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")
NEGATION = re.compile(r"\b(?:not|no|never|neither|nor|none|without)\b|n't\b", re.IGNORECASE)


def _negative(text: str) -> bool:
    return bool(NEGATION.search(text))


def _words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9][a-z0-9'-]*", text.lower()) if w not in STOP and len(w) > 2]


class LexicalVerifier:
    def __init__(self, threshold: float = 0.6):
        self.threshold = threshold

    def grounded(self, question: str, claim: str, sources: list[str]) -> tuple[bool, float | None]:
        text = "\n".join(sources)
        for value, _ in numeric.stated(claim):
            if not numeric.matches(text, float(value)):
                return False, 0.0
        if any(y not in text for y in YEAR.findall(claim)):
            return False, 0.0                 # numeric.stated skips years; a wrong year is still wrong
        words = _words(claim)
        if not words:
            return True, 1.0
        # The sentence that supports the claim best must agree with it on negation: "Juno was
        # not launched on an Atlas V" is not supported by "Juno was launched on an Atlas V".
        sentences = [s for s in SENTENCE.split(text) if s.strip()] or [text]
        best = max(sentences, key=lambda s: sum(w in set(_words(s)) for w in words))
        if _negative(claim) != _negative(best):
            return False, 0.0
        have = set(_words(text))
        cover = sum(w in have for w in words) / len(words)
        return cover >= self.threshold, round(cover, 3)


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
