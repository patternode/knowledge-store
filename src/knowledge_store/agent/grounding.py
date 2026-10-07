"""Grounding: no answer reaches a person unless every statement in it is shown in a source.

The agent answers as a list of claims, each citing passages with a verbatim quote. Before the
answer is shown, code (not the model) checks every citation:

    the passage exists and the caller may read it     read back through read_passages, as the caller
    the quote is in the passage                       after normalising case, spacing, quotes and dashes
    the quote is long enough to say something         MIN_QUOTE_CHARS
    the claim follows from its quotes (optional)      a Bedrock Guardrail contextual grounding check

A citation that fails is removed; a claim left with no citation is removed. The answer shown is
built from the claims that remain, so no sentence in it is unchecked text. When none remain, the
agent says it cannot answer from the sources, and what was missing.

The checks are plain functions of the claims and the passages, so they are tested without a model.
"""

from __future__ import annotations

import re
import unicodedata

from pydantic import BaseModel, Field

MIN_QUOTE_CHARS = 12
ABSTAIN = "I can't answer that from the sources in this collection."


class Citation(BaseModel):
    passage_id: str = Field(description="the id of a passage you read in this conversation")
    quote: str = Field(description="words copied exactly from that passage's text that state the claim: "
                                   "a phrase or a sentence, never paraphrased")


class Claim(BaseModel):
    text: str = Field(description="one statement that answers part of the question, in plain words")
    citations: list[Citation] = Field(description="at least one passage that states it, with the quote")


class GroundedAnswer(BaseModel):
    answerable: bool = Field(description="false when the passages you read do not answer the question")
    claims: list[Claim] = Field(description="the answer, as statements in reading order; empty when not answerable")
    gaps: list[str] = Field(default_factory=list,
                            description="what the sources could not say: a missing fact, type, relation or document")


_QUOTES = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'", "\u2032": "'",
                         "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u2033": '"',
                         "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-", "\u2014": "-",
                         "\u2015": "-", "\u2212": "-", "\u00a0": " "})


def normalise(text: str) -> str:
    t = unicodedata.normalize("NFKC", text or "").translate(_QUOTES)
    t = re.sub(r"[*_`#>|]", " ", t)            # markdown emphasis and table marks around the words
    return re.sub(r"\s+", " ", t).strip().casefold()


def quote_in(quote: str, passage: str) -> bool:
    q = normalise(quote).strip(" .,;:'\"()[]")
    return len(q) >= MIN_QUOTE_CHARS and q in normalise(passage)


def check(answer: GroundedAnswer, passages: dict[str, dict]) -> tuple[list[Claim], list[dict]]:
    """The claims that survive, with only their good citations; and every failure, with why.
    passages: id -> the passage as read_passages returned it to this caller."""
    kept, failures = [], []
    for i, c in enumerate(answer.claims):
        good = []
        for cit in c.citations:
            p = passages.get(cit.passage_id)
            if p is None:
                failures.append({"claim": i, "passage_id": cit.passage_id, "reason": "no such passage, or not readable"})
            elif not quote_in(cit.quote, p.get("text", "")):
                failures.append({"claim": i, "passage_id": cit.passage_id, "quote": cit.quote[:200],
                                 "reason": "quote not found in the passage" if len(normalise(cit.quote)) >= MIN_QUOTE_CHARS
                                 else "quote too short"})
            else:
                good.append(cit)
        if good and c.text.strip():
            kept.append(Claim(text=c.text.strip(), citations=good))
        elif not good:
            failures.append({"claim": i, "text": c.text[:200], "reason": "no citation survived; claim removed"})
    return kept, failures


def repair_prompt(failures: list[dict]) -> str:
    lines = [f"- claim {f['claim']}: {f['reason']}" + (f" (passage {f['passage_id']})" if f.get("passage_id") else "")
             + (f": {f['quote']!r}" if f.get("quote") else "") for f in failures]
    return ("Some citations did not check out against the passages:\n" + "\n".join(lines) +
            "\n\nRead the passages again with read_passages and answer again. Copy each quote exactly from the "
            "passage text. Drop any claim you cannot quote; if nothing is left, set answerable to false.")


def render(claims: list[Claim], passages: dict[str, dict], gaps: list[str]) -> dict:
    """The answer shown to the person: the claims in order, each with numbered links to its
    sources, and the sources with the quotes that support the answer."""
    if not claims:
        return {"answer": ABSTAIN, "abstained": True, "claims": [], "sources": [], "gaps": gaps}
    order: dict[str, int] = {}
    quotes: dict[str, list[str]] = {}
    out_claims, parts = [], []
    for c in claims:
        ns = []
        for cit in c.citations:
            n = order.setdefault(cit.passage_id, len(order) + 1)
            if n not in ns:
                ns.append(n)
            qs = quotes.setdefault(cit.passage_id, [])
            if cit.quote not in qs:
                qs.append(cit.quote)
        out_claims.append({"text": c.text, "sources": ns,
                           "citations": [{"passage_id": x.passage_id, "quote": x.quote} for x in c.citations]})
        parts.append(c.text.rstrip() + " " + "".join(f"[{n}]" for n in ns))
    sources = []
    for pid, n in sorted(order.items(), key=lambda kv: kv[1]):
        p = passages[pid]
        sources.append({"n": n, "passage_id": pid, "doc": p.get("doc"), "title": p.get("title"), "name": p.get("name"),
                        "text": p.get("text", ""), "quotes": quotes[pid], "source_uri": p.get("source_uri")})
    return {"answer": " ".join(parts), "abstained": False, "claims": out_claims, "sources": sources, "gaps": gaps}


def cited_ids(answer: GroundedAnswer) -> list[str]:
    return list(dict.fromkeys(c.passage_id for cl in answer.claims for c in cl.citations))
