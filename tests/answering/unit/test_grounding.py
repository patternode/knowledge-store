"""Grounding: every claim shown is backed by a passage quote, a cell value or a recomputed figure."""

from __future__ import annotations

import pytest

from knowledge_store.answering.domain import grounding as g
from knowledge_store.answering.domain.grounding import Citation, Claim, GroundedAnswer

PASSAGE = "Mission Alpha was launched by Agency Nova in 2021 aboard an Atlas V rocket."
PASSAGES = {"p1": {"text": PASSAGE, "doc": "d1", "title": "Alpha", "name": "alpha.md", "source_uri": "s3://x/alpha.md"}}
CELLS = {"c:1": {"value": "7800", "datatype": "decimal", "column": "cost", "table": "missions", "key": "alpha",
                 "class": "Mission", "row": [{"column": "name", "value": "Alpha"}, {"column": "cost", "value": "7800"}]},
         "c:bad": {"value": "n/a", "datatype": "decimal", "invalid": True}}
METRICS = {"m:launches": {"figure": 3, "metric": "atlas_v_launches", "description": "Atlas V launches"},
           "m:avg#Nova": {"figure": "12.345", "op": "avg", "attribute": "cost", "type": "Mission", "group_by": "agency"},
           "m:broken": {"error": "the metric is not published"}}


def answer(*claims: Claim) -> GroundedAnswer:
    return GroundedAnswer(answerable=True, claims=list(claims))


def quoted(text="launched by Agency Nova", pid="p1"):
    return Claim(text="Alpha was launched by Nova.", citations=[Citation(passage_id=pid, quote=text)])


# --- normalising and quotes ------------------------------------------------------------------

def test_normalise_folds_case_spacing_curly_quotes_and_dashes():
    assert g.normalise("  It’s  A—B “C” ") == "it's a-b \"c\""


def test_normalise_drops_markdown_marks_around_words():
    assert g.normalise("**Agency** _Nova_ | `x`") == "agency nova x"


def test_normalise_of_none_is_empty():
    assert g.normalise(None) == ""


def test_a_quote_in_the_passage_is_found_whatever_its_case_and_trailing_punctuation():
    assert g.quote_in("LAUNCHED BY AGENCY NOVA.", PASSAGE)


def test_a_quote_shorter_than_the_minimum_is_not_found_even_when_present():
    assert not g.quote_in("Agency", PASSAGE)


def test_a_paraphrase_is_not_a_quote():
    assert not g.quote_in("sent up by the Nova agency", PASSAGE)


# --- passage citations -----------------------------------------------------------------------

def test_a_claim_with_an_exact_quote_survives():
    kept, failures = g.check(answer(quoted()), PASSAGES)
    assert [c.text for c in kept] == ["Alpha was launched by Nova."] and failures == []


def test_a_citation_to_an_unreadable_passage_is_removed_with_its_claim():
    kept, failures = g.check(answer(quoted(pid="p9")), PASSAGES)
    assert kept == []
    assert failures[0]["reason"] == "no such passage, or not readable"
    assert failures[-1]["reason"] == "no citation survived; claim removed"


def test_a_misquote_is_reported_as_not_found():
    _, failures = g.check(answer(quoted("launched by Agency Orion")), PASSAGES)
    assert failures[0]["reason"] == "quote not found in the passage"


def test_a_short_quote_is_reported_as_too_short():
    _, failures = g.check(answer(quoted("Nova")), PASSAGES)
    assert failures[0]["reason"] == "quote too short"


def test_only_the_good_citations_of_a_claim_are_kept():
    claim = Claim(text="Alpha flew.", citations=[Citation(passage_id="p1", quote="aboard an Atlas V rocket"),
                                                 Citation(passage_id="p1", quote="aboard a Delta II rocket")])
    kept, failures = g.check(answer(claim), PASSAGES)
    assert len(kept[0].citations) == 1 and len(failures) == 1


def test_a_citation_naming_nothing_is_a_failure():
    _, failures = g.check(answer(Claim(text="x", citations=[Citation()])), PASSAGES)
    assert failures[0]["reason"] == "citation names neither a passage, a cell nor a metric"


def test_a_claim_with_blank_text_is_dropped_even_when_its_citation_holds():
    kept, failures = g.check(answer(Claim(text="  ", citations=[Citation(passage_id="p1", quote="launched by Agency Nova")])),
                             PASSAGES)
    assert kept == [] and failures == []


def test_a_kept_claims_text_is_trimmed():
    kept, _ = g.check(answer(Claim(text="  Alpha.  ", citations=[Citation(passage_id="p1", quote="launched by Agency Nova")])),
                      PASSAGES)
    assert kept[0].text == "Alpha."


# --- cell citations --------------------------------------------------------------------------

def test_a_cell_value_matches_as_a_number_whatever_its_formatting():
    kept, failures = g.check(answer(Claim(text="It cost 7,800.", citations=[Citation(cell_id="c:1", value="7,800")])),
                             {}, CELLS)
    assert kept and not failures


def test_a_wrong_cell_value_fails():
    _, failures = g.check(answer(Claim(text="It cost 9,000.", citations=[Citation(cell_id="c:1", value="9000")])), {}, CELLS)
    assert failures[0]["reason"] == "value does not equal the cell"


def test_a_missing_cell_fails():
    _, failures = g.check(answer(Claim(text="x", citations=[Citation(cell_id="c:none", value="1")])), {}, CELLS)
    assert failures[0]["reason"] == "no such cell, or not readable"


def test_an_invalid_cell_cannot_back_a_claim():
    _, failures = g.check(answer(Claim(text="x", citations=[Citation(cell_id="c:bad", value="n/a")])), {}, CELLS)
    assert failures[0]["reason"] == "the cell does not hold a valid value of its type"


def test_a_citation_naming_a_passage_and_a_cell_must_pass_both():
    cit = Citation(passage_id="p1", quote="launched by Agency Nova", cell_id="c:1", value="1")
    kept, failures = g.check(answer(Claim(text="x", citations=[cit])), PASSAGES, CELLS)
    assert kept == [] and failures[0]["reason"] == "value does not equal the cell"


def test_a_number_sent_for_a_value_is_read_as_text():
    assert Citation(cell_id="c:1", value=7800).value == "7800"
    assert Citation(value=None).value == ""


# --- metric citations ------------------------------------------------------------------------

def test_a_named_metrics_figure_matches():
    kept, _ = g.check(answer(Claim(text="3 launches.", citations=[Citation(metric_id="m:launches", figure="3")])),
                      {}, {}, METRICS)
    assert kept


def test_a_wrong_figure_fails_against_the_snapshot():
    _, failures = g.check(answer(Claim(text="4", citations=[Citation(metric_id="m:launches", figure="4")])), {}, {}, METRICS)
    assert failures[0]["reason"] == "figure does not match the snapshot"


def test_a_metric_that_failed_to_compute_reports_its_error():
    _, failures = g.check(answer(Claim(text="x", citations=[Citation(metric_id="m:broken", figure="1")])), {}, {}, METRICS)
    assert failures[0]["reason"] == "the metric is not published"


def test_an_unknown_metric_fails():
    _, failures = g.check(answer(Claim(text="x", citations=[Citation(metric_id="m:none", figure="1")])), {}, {}, METRICS)
    assert failures[0]["reason"] == "no such metric, or not readable"


def test_a_grouped_figure_is_checked_against_its_own_group():
    cit = Citation(metric_id="m:avg", group="Nova", figure="12.35")
    assert g.metric_key(cit) == "m:avg#Nova"
    kept, _ = g.check(answer(Claim(text="x", citations=[cit])), {}, {}, METRICS)
    assert kept


def test_a_figure_from_another_group_does_not_stand_in():
    _, failures = g.check(answer(Claim(text="x", citations=[Citation(metric_id="m:avg", group="Orion", figure="12.35")])),
                          {}, {}, METRICS)
    assert failures


def test_metric_key_without_a_group_is_the_id():
    assert g.metric_key(Citation(metric_id="m:x")) == "m:x"


@pytest.mark.parametrize("stated, figure, op, expected", [
    ("7,800", 7800, "", True),
    ("7800.0", "7800", "", True),
    ("12.35", "12.345", "avg", True),       # half up to the places stated
    ("12", "12.4", "avg", True),            # an average stated as a whole number
    ("12.34", "12.345", "avg", False),
    ("12.35", "12.345", "sum", False),      # only an average may be rounded
    ("Nova", "Nova", "", True),             # not numbers: compared as text
    ("Nova", "Orion", "", False),
    ("1", None, "", False),
])
def test_figure_matches(stated, figure, op, expected):
    assert g.figure_matches(stated, figure, op) is expected


# --- repair, render and the ids cited --------------------------------------------------------

def test_the_repair_prompt_names_each_failure_and_what_it_cited():
    text = g.repair_prompt([{"claim": 0, "reason": "quote not found in the passage", "passage_id": "p1", "quote": "abc"},
                            {"claim": 1, "reason": "value does not equal the cell", "cell_id": "c:1"},
                            {"claim": 2, "reason": "no such metric", "metric_id": "m:x"}])
    assert "- claim 0: quote not found in the passage (passage p1): 'abc'" in text
    assert "(cell c:1)" in text and "(metric m:x)" in text
    assert "set answerable to false" in text


def test_render_with_no_claims_abstains_and_keeps_the_gaps():
    out = g.render([], PASSAGES, ["no launch dates"])
    assert out == {"answer": g.ABSTAIN, "abstained": True, "claims": [], "sources": [], "gaps": ["no launch dates"]}


def test_render_numbers_sources_in_order_of_first_citation_and_reuses_numbers():
    c1 = Claim(text="Alpha launched.", citations=[Citation(passage_id="p1", quote="launched by Agency Nova")])
    c2 = Claim(text="It cost 7800.", citations=[Citation(cell_id="c:1", value="7800"),
                                                 Citation(passage_id="p1", quote="aboard an Atlas V rocket")])
    out = g.render([c1, c2], PASSAGES, [], CELLS)
    assert out["answer"] == "Alpha launched. [1] It cost 7800. [2][1]"
    passage, cell = out["sources"]
    assert passage["quotes"] == ["launched by Agency Nova", "aboard an Atlas V rocket"]
    assert passage["source_uri"] == "s3://x/alpha.md"
    assert cell["kind"] == "cell" and cell["title"] == "cost = 7800" and cell["name"] == "missions"
    assert out["claims"][1]["citations"] == [{"passage_id": "p1", "quote": "aboard an Atlas V rocket"},
                                             {"cell_id": "c:1", "value": "7800"}]


def test_render_describes_a_metric_source_and_its_group():
    c = Claim(text="Average 12.35.", citations=[Citation(metric_id="m:avg", group="Nova", figure="12.35")])
    out = g.render([c], {}, [], {}, METRICS)
    src = out["sources"][0]
    assert src["kind"] == "metric" and src["passage_id"] == "m:avg"
    assert src["title"].endswith("agency Nova") and "avg of cost over Mission" in src["title"]
    assert out["claims"][0]["citations"] == [{"metric_id": "m:avg", "figure": "12.35", "group": "Nova"}]


def test_render_a_metric_it_has_no_record_of_names_the_id():
    out = g.render([Claim(text="3.", citations=[Citation(metric_id="m:gone", figure="3")])], {}, [], {}, {})
    assert out["sources"][0]["title"] == "m:gone" and out["sources"][0]["text"] == "m:gone: 3"


def test_cited_ids_cells_and_metrics_are_unique_and_in_order():
    a = answer(Claim(text="x", citations=[Citation(passage_id="p2"), Citation(passage_id="p1"), Citation(cell_id="c:1"),
                                          Citation(metric_id="m:a", figure="1")]),
               Claim(text="y", citations=[Citation(passage_id="p2"), Citation(cell_id="c:1"), Citation(metric_id="m:a", figure="1")]))
    assert g.cited_ids(a) == ["p2", "p1"]
    assert g.cited_cells(a) == ["c:1"]
    assert g.cited_metrics(a) == [("m:a", "1")]


# --- what the guardrail checks a claim against ------------------------------------------------

def test_the_guardrail_source_of_a_passage_citation_is_its_text():
    assert g.guardrail_source(Citation(passage_id="p1"), PASSAGES, {}, {}) == PASSAGE


def test_the_guardrail_source_of_a_cell_carries_its_table_and_whole_row():
    src = g.guardrail_source(Citation(cell_id="c:1"), {}, CELLS, {})
    assert src == "Table missions, row alpha (Mission): name: Alpha; cost: 7800."


def test_the_guardrail_source_of_a_cell_without_its_row_is_the_cell():
    src = g.guardrail_source(Citation(cell_id="c:x"), {}, {"c:x": {"column": "cost", "value": "1", "table": "t", "key": "k"}}, {})
    assert src == "Table t, row k (row): cost: 1."


def test_the_guardrail_source_of_a_figure_says_what_it_was_computed_over():
    src = g.guardrail_source(Citation(metric_id="m:avg", group="Nova"), {}, {}, METRICS)
    assert src == "The avg of cost over Mission for agency Nova is 12.345."


def test_no_guardrail_source_for_a_failed_or_unknown_citation():
    assert g.guardrail_source(Citation(metric_id="m:broken"), {}, {}, METRICS) is None
    assert g.guardrail_source(Citation(passage_id="p9"), PASSAGES, {}, {}) is None


# --- the analyst's report models ---------------------------------------------------------------

def test_a_gap_report_needs_only_a_verdict_and_a_summary():
    r = g.GapReport(verdict="data_missing", summary="No document covers it.")
    assert r.ontology.classes == [] and r.rewrites == []


def test_a_filter_value_sent_as_a_number_is_text():
    assert g.FilterRef(attribute="cost", value=500).value == "500"
    assert g.FilterRef(value=None).value == ""
