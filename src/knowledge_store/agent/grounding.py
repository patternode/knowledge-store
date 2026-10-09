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


class FilterRef(BaseModel):
    attribute: str = ""
    op: str = "eq"
    value: str = ""


class Citation(BaseModel):
    passage_id: str = Field(default="", description="the id of a passage you read in this conversation, when the claim comes from a document")
    quote: str = Field(default="", description="words copied exactly from that passage's text that state the claim: "
                                   "a phrase or a sentence, never paraphrased")
    cell_id: str = Field(default="", description="the cell id a lookup_rows value carried (c:...), when the claim comes from a table")
    value: str = Field(default="", description="the cell's value, copied from the tool result")
    metric_id: str = Field(default="", description="the id an aggregate result carried (m:...), when the claim is a figure")
    figure: str = Field(default="", description="the figure, copied from the tool result")
    mapped_type: str = Field(default="", description="the mapped type, when the figure is an ad hoc aggregate rather than a named metric")
    attribute: str = Field(default="", description="the attribute an ad hoc sum, min, max or avg was taken over")
    filters: list[FilterRef] = Field(default_factory=list, description="the filters the figure was computed with, when it is not a named metric")


class Claim(BaseModel):
    text: str = Field(description="one statement that answers part of the question, in plain words")
    citations: list[Citation] = Field(description="at least one citation: a passage and a quote, a cell and its value, or a metric and its figure")


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


def _passage_ok(cit: Citation, passages: dict[str, dict], i: int, failures: list[dict]) -> bool:
    p = passages.get(cit.passage_id)
    if p is None:
        failures.append({"claim": i, "passage_id": cit.passage_id, "reason": "no such passage, or not readable"})
        return False
    if not quote_in(cit.quote, p.get("text", "")):
        failures.append({"claim": i, "passage_id": cit.passage_id, "quote": cit.quote[:200],
                         "reason": "quote not found in the passage" if len(normalise(cit.quote)) >= MIN_QUOTE_CHARS
                         else "quote too short"})
        return False
    return True


def _cell_ok(cit: Citation, cells: dict[str, dict], i: int, failures: list[dict]) -> bool:
    from ..structured.query import values_equal
    cell = cells.get(cit.cell_id)
    if cell is None:
        failures.append({"claim": i, "cell_id": cit.cell_id, "reason": "no such cell, or not readable"})
        return False
    if not values_equal(cit.value, str(cell.get("value", "")), cell.get("datatype") or "string"):
        failures.append({"claim": i, "cell_id": cit.cell_id, "value": cit.value[:200],
                         "reason": "value does not equal the cell"})
        return False
    return True


def _metric_ok(cit: Citation, metrics: dict[str, dict], i: int, failures: list[dict]) -> bool:
    from ..structured.query import values_equal
    metric = metrics.get(cit.metric_id)
    if metric is None:
        failures.append({"claim": i, "metric_id": cit.metric_id, "reason": "no such metric, or not readable"})
        return False
    if not values_equal(cit.figure, str(metric.get("figure", "")), "decimal" if _numeric(cit.figure) else "string"):
        failures.append({"claim": i, "metric_id": cit.metric_id, "figure": str(cit.figure)[:80],
                         "reason": "figure does not match the snapshot"})
        return False
    return True


def _numeric(text: str) -> bool:
    try:
        from decimal import Decimal
        Decimal(str(text).strip())
        return True
    except Exception:
        return False


def check(answer: GroundedAnswer, passages: dict[str, dict], cells: dict[str, dict] | None = None,
          metrics: dict[str, dict] | None = None) -> tuple[list[Claim], list[dict]]:
    """The claims that survive, with only their good citations; and every failure, with why.

    A passage citation is checked against the passage text. A cell citation is checked against
    the snapshot. A metric citation is checked against the figure recomputed from that snapshot.
    A claim that cites both a passage and a cell has to pass both. cells and metrics are what
    the tools returned when the checker re-read them: id -> the cell or the metric.
    """
    cells, metrics = cells or {}, metrics or {}
    kept, failures = [], []
    for i, c in enumerate(answer.claims):
        good = []
        for cit in c.citations:
            used = False
            ok = True
            if cit.passage_id or cit.quote:
                used = True
                ok = _passage_ok(cit, passages, i, failures) and ok
            if cit.cell_id or cit.value:
                used = True
                ok = _cell_ok(cit, cells, i, failures) and ok
            if cit.metric_id or cit.figure:
                used = True
                ok = _metric_ok(cit, metrics, i, failures) and ok
            if not used:
                failures.append({"claim": i, "reason": "citation names neither a passage, a cell nor a metric"})
            elif ok:
                good.append(cit)
        if good and c.text.strip():
            kept.append(Claim(text=c.text.strip(), citations=good))
        elif not good:
            failures.append({"claim": i, "text": c.text[:200], "reason": "no citation survived; claim removed"})
    return kept, failures


def repair_prompt(failures: list[dict]) -> str:
    lines = [f"- claim {f['claim']}: {f['reason']}"
             + (f" (passage {f['passage_id']})" if f.get("passage_id") else "")
             + (f" (cell {f['cell_id']})" if f.get("cell_id") else "")
             + (f" (metric {f['metric_id']})" if f.get("metric_id") else "")
             + (f": {f['quote']!r}" if f.get("quote") else "") for f in failures]
    return ("Some citations did not check out:\n" + "\n".join(lines) +
            "\n\nRead the passages again with read_passages, and re-read table cells with lookup_rows. "
            "Copy each quote exactly from the passage text, and each cell value exactly from the tool. "
            "Drop any claim you cannot cite; if nothing is left, set answerable to false.")


def render(claims: list[Claim], passages: dict[str, dict], gaps: list[str],
           cells: dict[str, dict] | None = None) -> dict:
    """The answer shown to the person: the claims in order, each with numbered links to its
    sources, and the sources with the quotes that support the answer."""
    if not claims:
        return {"answer": ABSTAIN, "abstained": True, "claims": [], "sources": [], "gaps": gaps}
    cells = cells or {}
    order: dict[str, int] = {}
    quotes: dict[str, list[str]] = {}
    out_claims, parts = [], []
    for c in claims:
        ns = []
        for cit in c.citations:
            if cit.passage_id:
                n = order.setdefault(cit.passage_id, len(order) + 1)
                if n not in ns:
                    ns.append(n)
                qs = quotes.setdefault(cit.passage_id, [])
                if cit.quote not in qs:
                    qs.append(cit.quote)
            if cit.cell_id:
                n = order.setdefault(cit.cell_id, len(order) + 1)
                if n not in ns:
                    ns.append(n)
                qs = quotes.setdefault(cit.cell_id, [])
                if cit.value not in qs:
                    qs.append(cit.value)
            if cit.metric_id:
                n = order.setdefault(cit.metric_id, len(order) + 1)
                if n not in ns:
                    ns.append(n)
                qs = quotes.setdefault(cit.metric_id, [])
                if cit.figure not in qs:
                    qs.append(cit.figure)
        cited = [{"passage_id": x.passage_id, "quote": x.quote} for x in c.citations if x.passage_id]
        cited += [{"cell_id": x.cell_id, "value": x.value} for x in c.citations if x.cell_id]
        cited += [{"metric_id": x.metric_id, "figure": x.figure} for x in c.citations if x.metric_id]
        out_claims.append({"text": c.text, "sources": ns, "citations": cited})
        parts.append(c.text.rstrip() + " " + "".join(f"[{n}]" for n in ns))
    sources = []
    for pid, n in sorted(order.items(), key=lambda kv: kv[1]):
        if pid in passages:
            p = passages[pid]
            sources.append({"n": n, "passage_id": pid, "doc": p.get("doc"), "title": p.get("title"), "name": p.get("name"),
                            "text": p.get("text", ""), "quotes": quotes[pid], "source_uri": p.get("source_uri")})
        elif pid in cells:
            c = cells[pid]
            sources.append({"n": n, "passage_id": pid, "kind": "cell", "title": f"{c.get('column')} = {c.get('value')}",
                            "text": f"{c.get('column')}: {c.get('value')}", "quotes": quotes[pid],
                            "name": c.get("table"), "row": list(c.get("row") or [])})
        else:
            sources.append({"n": n, "passage_id": pid, "kind": "metric", "title": pid,
                            "text": quotes[pid][0] if quotes[pid] else "", "quotes": quotes[pid]})
    return {"answer": " ".join(parts), "abstained": False, "claims": out_claims, "sources": sources, "gaps": gaps}


def cited_ids(answer: GroundedAnswer) -> list[str]:
    return list(dict.fromkeys(c.passage_id for cl in answer.claims for c in cl.citations if c.passage_id))


def cited_cells(answer: GroundedAnswer) -> list[str]:
    return list(dict.fromkeys(c.cell_id for cl in answer.claims for c in cl.citations if c.cell_id))


def cited_metrics(answer: GroundedAnswer) -> list[tuple[str, str]]:
    """(metric id, figure) for each metric a claim cites."""
    return list(dict.fromkeys((c.metric_id, c.figure) for cl in answer.claims for c in cl.citations if c.metric_id))


# --- the analyst's report (workbench.REPORT_SCHEMA, as models for structured output) ---------------

class NewClass(BaseModel):
    name: str = Field(description="the class name, in the ontology's naming style")
    parent: str = Field(default="", description="the existing class it is a kind of")
    definition: str
    why: str = Field(default="", description="what in the question needs it")


class NewRelation(BaseModel):
    name: str
    domain: str = Field(default="", description="the class it runs from")
    range: str = Field(default="", description="the class it runs to")
    definition: str
    why: str = ""


class NewAttribute(BaseModel):
    name: str
    domain: str = Field(default="", description="the class it describes")
    datatype: str = Field(default="string", description="string, integer, decimal, date or boolean")
    definition: str
    why: str = ""


class OntologyChange(BaseModel):
    classes: list[NewClass] = Field(default_factory=list)
    relations: list[NewRelation] = Field(default_factory=list)
    attributes: list[NewAttribute] = Field(default_factory=list)


class ExistingTerm(BaseModel):
    term: str
    kind: str = Field(default="", description="class, relation or attribute")
    use: str = Field(default="", description="how it would carry the answer")


class DataNeed(BaseModel):
    what: str = Field(description="the facts or documents that are missing")
    where: str = Field(default="", description="the kind of source that would hold them")
    why: str = ""


class MissedFact(BaseModel):
    what: str = Field(description="the fact a passage states that the graph lacks")
    passage_id: str = ""
    why: str = ""


class GapReport(BaseModel):
    verdict: str = Field(description="answerable, data_missing, ontology_missing, extraction_missed or out_of_scope")
    summary: str = Field(description="two or three sentences: why it cannot be answered now, and what would fix it")
    ontology: OntologyChange = Field(default_factory=OntologyChange)
    existing: list[ExistingTerm] = Field(default_factory=list)
    data: list[DataNeed] = Field(default_factory=list)
    extraction: list[MissedFact] = Field(default_factory=list)
    rewrites: list[str] = Field(default_factory=list, description="questions close to this one the graph answers now")
