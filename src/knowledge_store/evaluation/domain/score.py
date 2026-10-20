"""Scoring one answer against one question of an evaluation set. Deterministic: no model judges.

The set format is in sets.py. Measures, per question:

    correct          answerable: every fact and figure stated, none forbidden, comparison in order;
                     unanswerable: the agent declined (abstained, or said what the sources lack)
                     and stated nothing the set forbids
    score            the share of facts and figures stated (0 if a forbidden one is, or the order is wrong)
    abstained        the agent said the sources do not answer it, and made no claims
    declined         abstained, or answered only with what the sources lack (its gaps)
    grounded         the share of the agent's proposed claims that survived its own citation checks
    source_hit       an expected document is among the cited sources
    citation_precision, citation_recall
                     of the documents cited, the share the set expects; of those expected, the share cited
    claims, unsupported, supported_share
                     the claims shown, and, when a claim verifier ran, how many it rejected

Every reply falls into one of these, by whether the sources answer the question and what the
agent did (patternode-architecture ADR-048):

    right answer       answerable, and the agent gave it
    right decline      unanswerable, and the agent declined
    false answer       unanswerable, and the agent stated a fact as the answer
    false abstention   answerable, and the agent declined
    unsupported claim  any claim, on any question, that the claim verifier rejects

The old "false positive" (answered an unanswerable question, judged by the abstained flag
alone) counted a cited hedge as a false answer and never counted a wrong claim on an answerable
question, so it is retired.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

from knowledge_store.evaluation.domain import numeric
from knowledge_store.evaluation.domain.sets import KINDS, EvalSet, Question, parse  # noqa: F401  (re-exported)

_DASHES = re.compile("[‐-―−]")
# What a reply says when it declines: used only when the reply carries no gaps of its own (an
# answer from another system, or over an API that drops them).
_DECLINES = re.compile(r"\b(?:can(?:no|')t answer|cannot be answered|(?:do|does|did) not (?:say|state|mention|name|give)|"
                       r"(?:is|are) not (?:stated|mentioned|given|named)|no (?:information|mention)|not in the sources|"
                       r"the sources (?:do not|don't))\b", re.IGNORECASE)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", _DASHES.sub("-", text or "")).casefold()


def _pattern(spelling: str) -> str:
    s = _norm(spelling)
    return (r"\b" if s[:1].isalnum() else "") + re.escape(s) + (r"\b" if s[-1:].isalnum() else "")


def position(text: str, spellings: list[str]) -> int | None:
    t = _norm(text)
    hits = [m.start() for s in spellings for m in [re.search(_pattern(s), t)] if m]
    return min(hits) if hits else None


def declined(result: dict) -> bool:
    """The agent declined: it abstained, or it answered only with what the sources lack."""
    if result.get("abstained"):
        return True
    if result.get("gaps"):
        return True
    return "gaps" not in result and bool(_DECLINES.search(result.get("answer") or ""))


def _cited(result: dict) -> set[str]:
    out = set()
    for s in result.get("sources") or []:
        for k in ("name", "title", "doc"):
            if s.get(k):
                out.add(str(s[k]))
    return out


def _hit(cited: set[str], expected: str) -> bool:
    return any(c == expected or c.endswith("/" + expected) or expected.endswith("/" + c) or Path(expected).name == c
               for c in cited)


def score(q: Question, result: dict, verdicts: list[dict] | None = None) -> dict:
    """verdicts: one per claim shown, {"supported": bool, "score": float | None}, from a claim
    verifier, or None when none ran."""
    answer = result.get("answer") or ""
    abstained = bool(result.get("abstained"))
    did_decline = declined(result)
    g = result.get("grounding") or {}
    proposed, shown = g.get("claims_proposed"), g.get("claims_shown")
    grounded = round(shown / proposed, 3) if proposed else None
    cited = _cited(result)
    source_hit = precision = recall = None
    if q.sources and not abstained:
        source_hit = any(_hit(cited, s) for s in q.sources)
        docs = {c for c in cited if "/" in c or "." in c}
        if docs:
            precision = round(sum(any(_hit({c}, s) for s in q.sources) for c in docs) / len(docs), 3)
        recall = round(sum(_hit(cited, s) for s in q.sources) / len(q.sources), 3)
    claims = len(result.get("claims") or []) if not abstained else 0
    unsupported = sum(1 for v in verdicts or [] if not v.get("supported", True)) if verdicts is not None else None
    supported_share = round(1 - unsupported / len(verdicts), 3) if verdicts else None
    forbidden = [s for s in q.must_not if position(answer, [s]) is not None]
    base = {"id": q.id, "kind": q.kind, "family": q.family, "answerable": q.answerable, "abstained": abstained,
            "declined": did_decline, "grounded": grounded, "source_hit": source_hit, "citation_precision": precision,
            "citation_recall": recall, "claims": claims, "unsupported": unsupported, "supported_share": supported_share,
            "error": result.get("error")}
    if not q.answerable:
        ok = did_decline and not forbidden and not result.get("error")
        return {**base, "correct": ok, "score": 1.0 if ok else 0.0, "missing": [], "forbidden": forbidden,
                "false_answer": not ok and not result.get("error"), "false_abstention": False}
    found = [position(answer, m) is not None for m in q.must]
    figs = [numeric.matches(answer, f["value"], f.get("tolerance")) for f in q.figures]
    order_ok = True
    if q.first:
        right, wrong = position(answer, [q.first[0]]), position(answer, [q.first[1]])
        order_ok = right is not None and (wrong is None or right < wrong)
    stated = found + figs
    value = 0.0 if forbidden or not order_ok else sum(stated) / len(stated)
    missing = [m[0] for m, ok in zip(q.must, found) if not ok] + [str(f["value"]) for f, ok in zip(q.figures, figs) if not ok]
    if result.get("error"):
        value = 0.0
    return {**base, "correct": value == 1.0, "score": round(value, 3), "missing": missing, "forbidden": forbidden,
            "order_ok": order_ok, "false_answer": False, "false_abstention": abstained and not result.get("error")}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    """The 95% Wilson interval for k right out of n: small sets move a lot on one question."""
    if not n:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(max(0.0, c - h), 3), round(min(1.0, c + h), 3)


def _mean(xs: list) -> float | None:
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 3) if xs else None


def families(rows: list[dict]) -> dict:
    """Paraphrase families: the questions asking one thing in other words should all be right or
    all be wrong. consistent is the share of families whose members agree."""
    fam: dict[str, list[bool]] = {}
    for r in rows:
        if r.get("family"):
            fam.setdefault(r["family"], []).append(bool(r["correct"]))
    multi = {k: v for k, v in fam.items() if len(v) > 1}
    if not multi:
        return {}
    return {"families": len(multi), "consistent": round(sum(len(set(v)) == 1 for v in multi.values()) / len(multi), 3),
            "split": sorted(k for k, v in multi.items() if len(set(v)) > 1)}


def summarise(rows: list[dict]) -> dict:
    def block(sel: list[dict]) -> dict:
        n = len(sel)
        k = sum(r["correct"] for r in sel)
        verified = [r for r in sel if r.get("unsupported") is not None]
        return {"questions": n, "correct": k,
                "accuracy": round(k / n, 3) if n else None, "accuracy_ci95": wilson(k, n),
                "mean_score": round(sum(r["score"] for r in sel) / n, 3) if n else None,
                "grounded": _mean([r["grounded"] for r in sel]),
                "source_hit_rate": _mean([None if r["source_hit"] is None else float(r["source_hit"]) for r in sel]),
                "citation_precision": _mean([r.get("citation_precision") for r in sel]),
                "citation_recall": _mean([r.get("citation_recall") for r in sel]),
                "false_answers": sum(bool(r.get("false_answer")) for r in sel),
                "false_abstentions": sum(bool(r.get("false_abstention")) for r in sel),
                "claims_verified": sum(r.get("claims") or 0 for r in verified) if verified else None,
                "unsupported_claims": sum(r["unsupported"] for r in verified) if verified else None,
                "supported_share": _mean([r.get("supported_share") for r in verified]) if verified else None,
                "errors": sum(1 for r in sel if r.get("error"))}
    out = {"all": block(rows)}
    for k in KINDS:
        sel = [r for r in rows if r["kind"] == k]
        if sel:
            out[k] = block(sel)
    fam = families(rows)
    if fam:
        out["families"] = fam
    return out
