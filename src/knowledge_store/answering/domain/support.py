"""Support: whether a claim follows from the passage, cell or figure it cites.

The quote check (grounding.check) proves that the quoted text is in the passage. It does not prove
that the claim follows from it: "Juno launched in 1999" can cite the real quote "Juno is a NASA
probe". The lexical verifier is a deterministic floor for that second question: every number and
year the claim states is in its sources, the best-matching source sentence agrees with the claim
on negation, and most of the claim's content words appear in the sources. It is not a judge of
meaning, and it runs on every claim at answer time because it is cheap and needs no model.

It implements answering.ports.ClaimVerifier. Evaluation re-exports it, so an evaluation measures
what production enforces (patternode-architecture ADR-048).
"""

from __future__ import annotations

import re

from knowledge_store.kernel import numeric

STOP = set("""a an and are as at be been by for from has have in into is it its of on or that the their this to was were
which with will would its they them he she his her we our you your than then there these those also about""".split())


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
