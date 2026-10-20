"""Run a set: ask every question, verify each claim, check truth sources, score, summarise.

One failed question scores zero and the run goes on. A cost budget stops the run before a
question that would pass it, using the tokens the answers report.
"""

from __future__ import annotations

import datetime as dt
import time
from typing import Callable

from knowledge_store.evaluation.domain import score as scoring
from knowledge_store.evaluation.domain.sets import EvalSet, Question
from knowledge_store.evaluation.ports import Answerer, ClaimVerifier, Grader, Runner, TruthSource


def claim_sources(result: dict, claim: dict) -> list[str]:
    """What a claim rests on, as text: each cited passage's text, a cell as `column: value`, a
    metric as its figure."""
    by_n = {s.get("n"): s for s in result.get("sources") or []}
    out = []
    for n in claim.get("sources") or []:
        s = by_n.get(n) or {}
        if s.get("text"):
            out.append(str(s["text"]))
    for c in claim.get("citations") or []:
        if c.get("cell_id") and c.get("value") is not None:
            out.append(f"{c.get('column') or 'value'}: {c['value']}")
        if c.get("metric_id") and c.get("figure") is not None:
            out.append(str(c["figure"]))
    return out


def verify(question: Question, result: dict, verifier: ClaimVerifier | None) -> list[dict] | None:
    if verifier is None or result.get("abstained") or result.get("error"):
        return None
    out = []
    for c in result.get("claims") or []:
        sources = claim_sources(result, c)
        if not sources:
            out.append({"claim": c.get("text", ""), "supported": False, "score": None, "why": "cites nothing readable"})
            continue
        ok, sc = verifier.grounded(question.question, c.get("text", ""), sources)
        out.append({"claim": c.get("text", ""), "supported": bool(ok), "score": sc})
    return out


def plain_runner(questions, ask, score_one):
    """The default Runner: a loop, no framework."""
    return [(q, res, score_one(q, res)) for q in questions for res in [ask(q)]]


def tokens(rows: list[dict]) -> dict:
    total = {"inputTokens": 0, "outputTokens": 0}
    for r in rows:
        for k in total:
            total[k] += int((r.get("usage") or {}).get(k) or 0)
    return total


def run(evalset: EvalSet, ask: Answerer, *, only: list[str] | None = None, verifier: ClaimVerifier | None = None,
        truth: list[TruthSource] | None = None, grader: Grader | None = None, runner: Runner | None = None,
        max_tokens: int | None = None, progress: Callable[[str], None] = print,
        now: Callable[[], dt.datetime] = lambda: dt.datetime.now(dt.UTC)) -> dict:
    questions = [q for q in evalset.questions if not only or q.id in only]
    spent = {"tokens": 0}
    results: dict[str, dict] = {}

    def guarded(q: Question) -> dict:
        started = time.monotonic()
        if max_tokens is not None and spent["tokens"] >= max_tokens:
            res = {"error": "skipped: the run's token budget is spent", "abstained": True}
        else:
            try:
                res = ask(q)
            except Exception as e:  # one failed question scores zero; the run goes on
                res = {"error": f"{type(e).__name__}: {str(e)[:300]}", "abstained": True}
        u = res.get("usage") or {}
        spent["tokens"] += int(u.get("inputTokens") or 0) + int(u.get("outputTokens") or 0)
        res.setdefault("_seconds", round(time.monotonic() - started, 1))
        return res

    def score_one(q: Question, res: dict) -> dict:
        verdicts = verify(q, res, verifier)
        row = scoring.score(q, res, verdicts)
        checks = {t.name: t.check(q, res) for t in truth or []}
        failed = [k for k, v in checks.items() if v.get("ok") is False]
        if failed:
            row["correct"], row["score"] = False, 0.0
        row.update(truth=checks or None, verdicts=verdicts, seconds=res.get("_seconds"), usage=res.get("usage"),
                   tool_calls=len(res.get("tool_calls") or []))
        if grader is not None and not res.get("error"):
            row["grade"] = grader.grade(q, res)  # reported beside the score, never folded into it
        results[q.id] = res
        progress(f"{q.id} {q.kind:<12} {'PASS' if row['correct'] else 'FAIL'} score={row['score']} "
                 f"grounded={row['grounded']} unsupported={row['unsupported']}")
        return row

    triples = (runner or plain_runner)(questions, guarded, score_one)
    rows = [row for _, _, row in triples]
    return {"set": evalset.name, "collection": evalset.collection, "when": now().isoformat(timespec="seconds"),
            "summary": scoring.summarise(rows), "rows": rows,
            "results": [{"id": q.id, "question": q.question, "expected": q.expected,
                         "result": {k: v for k, v in res.items() if k != "_seconds"}} for q, res, _ in triples],
            "tokens": tokens(rows)}
