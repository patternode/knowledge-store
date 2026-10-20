"""An evaluation set: a collection and its questions, with what a right answer states.

The format, as YAML:

    collection: missions
    name: space-missions                 optional; the file name otherwise
    questions:
    - id: q01
      kind: lookup                       lookup | list | multi-hop | aggregate | comparison | unanswerable
      question: Which rocket launched Juno?
      must: [[Atlas V 551, Atlas V]]     facts the answer has to state; each is a list of spellings, any
                                         one counts, matched on word boundaries ignoring case
      must_not: [Delta II]               spellings whose presence fails the answer (the near miss)
      first: [Voyager 2, Voyager 1]      comparisons: the first must be named before the second
      figures: [{value: 2.2e9}]          numbers the answer has to state, each within the rounding the
                                         answer states it at, or within `tolerance` (relative) if given
      sources: [outer-planets/juno.json] documents (file names) the answer should cite; any one counts
      answerable: true                   false: the sources do not answer it, and the agent must say so
      private: false                     ask as a caller who may read private sources
      family: juno-rocket                questions that ask the same thing in other words share a family
      judged: false                      true: the set states no fact; an application's truth sources or a
                                         grader judge the answer, and the score checks only that it answered
      context: {}                        application data its truth sources read (a metric, a company id);
                                         the scorer ignores it

Parsing is pure; reading the file is the set_files adapter's job.
"""

from __future__ import annotations

from dataclasses import dataclass, field

KINDS = ("lookup", "list", "multi-hop", "aggregate", "comparison", "unanswerable")


@dataclass
class Question:
    id: str
    question: str
    kind: str = "lookup"
    must: list[list[str]] = field(default_factory=list)
    must_not: list[str] = field(default_factory=list)
    first: list[str] = field(default_factory=list)
    figures: list[dict] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    answerable: bool = True
    private: bool = False
    family: str = ""
    judged: bool = False
    context: dict = field(default_factory=dict)
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


def parse(data: dict, name: str = "") -> EvalSet:
    """An evaluation set from its parsed YAML, checked."""
    qs = []
    for q in data["questions"]:
        q = dict(q)
        q["must"] = [m if isinstance(m, list) else [m] for m in q.get("must") or []]
        q["figures"] = [f if isinstance(f, dict) else {"value": f} for f in q.get("figures") or []]
        qs.append(Question(**q))
    ids = [q.id for q in qs]
    if len(ids) != len(set(ids)):
        raise ValueError("question ids must be unique")
    for q in qs:
        if q.kind not in KINDS:
            raise ValueError(f"{q.id}: kind must be one of {KINDS}, not {q.kind!r}")
        if q.kind == "unanswerable" and q.answerable:
            raise ValueError(f"{q.id}: kind unanswerable needs answerable: false")
        if q.answerable and not (q.must or q.figures or q.judged):
            raise ValueError(f"{q.id}: an answerable question needs at least one fact in must or figures, or judged: true")
        if q.first and len(q.first) != 2:
            raise ValueError(f"{q.id}: first names two candidates, the correct one first")
        for f in q.figures:
            if not isinstance(f.get("value"), (int, float)):
                raise ValueError(f"{q.id}: each figure needs a numeric value")
    return EvalSet(collection=data["collection"], questions=qs, name=data.get("name") or name)
