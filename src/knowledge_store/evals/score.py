"""Scoring one answer against one question of an evaluation set. Deterministic: no model judges.

An evaluation set (YAML) is a collection and its questions:

    collection: missions
    questions:
    - id: q01
      kind: lookup                       lookup | list | multi-hop | aggregate | comparison | unanswerable
      question: Which rocket launched Juno?
      must: [[Atlas V 551, Atlas V]]     facts the answer has to state; each is a list of spellings, any
                                         one counts, matched on word boundaries ignoring case
      must_not: [Delta II]               spellings whose presence fails the answer (the near miss)
      first: [Voyager 2, Voyager 1]      comparisons: the first must be named before the second
      sources: [outer-planets/juno.json] documents (file names) the answer should cite; any one counts
      answerable: true                   false: the sources do not answer it, and the agent must say so
      private: false                     ask as a caller who may read private sources

Measures, per question:

    correct      answerable: every fact stated, none forbidden, comparison in order;
                 unanswerable: the agent abstained
    score        the share of facts stated (0 if a forbidden one is, or the order is wrong)
    abstained    the agent said the sources do not answer it
    grounded     the share of the agent's proposed claims that survived the citation checks; what
                 did not survive was an unsupported statement that the checks stopped
    source_hit   an expected document is among the cited sources

Every reply is one of four outcomes, by whether the sources answer the question and whether the
agent answered it:

    true positive    answerable, and the agent gave the answer
    true negative    unanswerable, and the agent declined
    false positive   a statement whose meaning is not in the passage it rests on. The citation
                     checks stop most of them before they are shown (grounded); the report counts
                     the ones that got through as unanswerable questions the agent answered
    false negative   answerable, and the agent declined. Often the ontology or the knowledge base
                     does not support the question yet
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

KINDS = ("lookup", "list", "multi-hop", "aggregate", "comparison", "unanswerable")


@dataclass
class Question:
    id: str
    question: str
    kind: str = "lookup"
    must: list[list[str]] = field(default_factory=list)
    must_not: list[str] = field(default_factory=list)
    first: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    answerable: bool = True
    private: bool = False
    expected: str = ""
    note: str = ""
    # How an offline smoke test reads this question from a mapped table. The scorer ignores it.
    # A live eval still scores the answer text; source names may be the logical table.
    structured: dict | None = None


@dataclass
class EvalSet:
    collection: str
    questions: list[Question]
    name: str = ""


def load(path: Path) -> EvalSet:
    import yaml
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    qs = []
    for q in data["questions"]:
        q = dict(q)
        q["must"] = [m if isinstance(m, list) else [m] for m in q.get("must") or []]
        qs.append(Question(**q))
    ids = [q.id for q in qs]
    if len(ids) != len(set(ids)):
        raise ValueError("question ids must be unique")
    for q in qs:
        if q.kind not in KINDS:
            raise ValueError(f"{q.id}: kind must be one of {KINDS}, not {q.kind!r}")
        if q.kind == "unanswerable" and q.answerable:
            raise ValueError(f"{q.id}: kind unanswerable needs answerable: false")
        if q.answerable and not q.must:
            raise ValueError(f"{q.id}: an answerable question needs at least one fact in must")
        if q.first and len(q.first) != 2:
            raise ValueError(f"{q.id}: first names two candidates, the correct one first")
    return EvalSet(collection=data["collection"], questions=qs, name=data.get("name") or Path(path).stem)


_DASHES = re.compile("[‐-―−]")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", _DASHES.sub("-", text or "")).casefold()


def _pattern(spelling: str) -> str:
    s = _norm(spelling)
    return (r"\b" if s[:1].isalnum() else "") + re.escape(s) + (r"\b" if s[-1:].isalnum() else "")


def position(text: str, spellings: list[str]) -> int | None:
    t = _norm(text)
    hits = [m.start() for s in spellings for m in [re.search(_pattern(s), t)] if m]
    return min(hits) if hits else None


def score(q: Question, result: dict) -> dict:
    answer = result.get("answer") or ""
    abstained = bool(result.get("abstained"))
    g = result.get("grounding") or {}
    proposed, shown = g.get("claims_proposed"), g.get("claims_shown")
    grounded = round(shown / proposed, 3) if proposed else None
    cited = {s.get("name") for s in result.get("sources") or []} | {s.get("title") for s in result.get("sources") or []}
    source_hit = None
    if q.sources and not abstained:
        source_hit = any(any(c and (c == s or c.endswith("/" + s) or s.endswith("/" + c) or Path(s).name == c)
                             for c in cited) for s in q.sources)
    base = {"id": q.id, "kind": q.kind, "answerable": q.answerable, "abstained": abstained, "grounded": grounded,
            "source_hit": source_hit, "error": result.get("error")}
    if not q.answerable:
        return {**base, "correct": abstained, "score": 1.0 if abstained else 0.0, "missing": [], "forbidden": []}
    found = [position(answer, m) is not None for m in q.must]
    forbidden = [s for s in q.must_not if position(answer, [s]) is not None]
    order_ok = True
    if q.first:
        right, wrong = position(answer, [q.first[0]]), position(answer, [q.first[1]])
        order_ok = right is not None and (wrong is None or right < wrong)
    value = 0.0 if forbidden or not order_ok else sum(found) / len(found)
    return {**base, "correct": value == 1.0, "score": round(value, 3),
            "missing": [m[0] for m, ok in zip(q.must, found) if not ok], "forbidden": forbidden, "order_ok": order_ok}


def summarise(rows: list[dict]) -> dict:
    def block(sel: list[dict]) -> dict:
        n = len(sel)
        grounded = [r["grounded"] for r in sel if r["grounded"] is not None]
        hits = [r["source_hit"] for r in sel if r["source_hit"] is not None]
        ans = [r for r in sel if r["answerable"]]
        unans = [r for r in sel if not r["answerable"]]
        return {"questions": n, "correct": sum(r["correct"] for r in sel),
                "accuracy": round(sum(r["correct"] for r in sel) / n, 3) if n else None,
                "mean_score": round(sum(r["score"] for r in sel) / n, 3) if n else None,
                "grounded": round(sum(grounded) / len(grounded), 3) if grounded else None,
                "source_hit_rate": round(sum(hits) / len(hits), 3) if hits else None,
                "false_abstentions": sum(r["abstained"] for r in ans),
                "missed_abstentions": sum(not r["abstained"] for r in unans),
                "errors": sum(1 for r in sel if r.get("error"))}
    out = {"all": block(rows)}
    for k in KINDS:
        sel = [r for r in rows if r["kind"] == k]
        if sel:
            out[k] = block(sel)
    return out
