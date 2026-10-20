"""Scoring one reply against one question, and summarising a run. Deterministic: no model judges
(patternode-architecture ADR-048)."""

from __future__ import annotations

import pytest

from knowledge_store.evaluation.domain.score import declined, families, position, score, summarise, wilson
from knowledge_store.evaluation.domain.sets import Question


def q(**kw):
    return Question(**{"id": "x", "question": "?", "must": [["Atlas V 551", "Atlas V"]], **kw})


def unanswerable(**kw):
    return q(kind="unanswerable", answerable=False, must=[], **kw)


def reply(text="", *, claims=(), sources=(), abstained=False, gaps=None, proposed=None, shown=None, **extra):
    r = {"answer": text, "abstained": abstained, "claims": list(claims), "sources": list(sources), **extra}
    if proposed is not None:
        r["grounding"] = {"claims_proposed": proposed, "claims_shown": shown}
    if gaps is not None:
        r["gaps"] = gaps
    return r


# --- matching spellings ---------------------------------------------------------------------------

def test_a_spelling_matches_on_word_boundaries_ignoring_case():
    assert position("It flew on an atlas v rocket.", ["Atlas V"]) == 14
    assert position("an Atlas Vx", ["Atlas V"]) is None


def test_the_earliest_of_several_spellings_counts():
    assert position("JUNO then Atlas", ["Atlas", "Juno"]) == 0


def test_dashes_and_spaces_are_normalised():
    assert position("Apollo–11   landed", ["Apollo-11 landed"]) == 0


def test_a_spelling_ending_in_punctuation_needs_no_word_boundary():
    assert position("cost $5.", ["$5."]) is not None


# --- declining ------------------------------------------------------------------------------------

def test_abstaining_is_declining():
    assert declined({"abstained": True, "answer": "Ireland"})


def test_answering_only_with_gaps_is_declining():
    assert declined({"answer": "He is described as well born.", "gaps": ["birthplace"]})


def test_with_empty_gaps_the_text_is_not_consulted():
    assert not declined({"answer": "The sources do not say.", "gaps": []})


@pytest.mark.parametrize("text", ["I can't answer that.", "The stories do not say where.", "His birthplace is not stated.",
                                  "There is no information on it.", "That is not in the sources."])
def test_without_gaps_a_declining_phrase_is_declining(text):
    assert declined({"answer": text})


def test_without_gaps_a_plain_answer_is_not_declining():
    assert not declined({"answer": "He was born in Kent."}) and not declined({})


# --- answerable questions -------------------------------------------------------------------------

def test_every_fact_stated_is_a_right_answer():
    r = score(q(), reply("Juno launched on an Atlas V."))
    assert r["correct"] and r["score"] == 1.0 and r["missing"] == [] and not r["false_abstention"]


def test_the_score_is_the_share_of_facts_and_figures_stated():
    r = score(q(must=[["Juno"], ["Atlas"]], figures=[{"value": 2011}]), reply("Juno."))
    assert not r["correct"] and r["score"] == round(1 / 3, 3) and r["missing"] == ["Atlas", "2011"]


def test_a_forbidden_spelling_scores_zero():
    r = score(q(must_not=["Delta II"]), reply("Atlas V, not a Delta II."))
    assert not r["correct"] and r["score"] == 0.0 and r["forbidden"] == ["Delta II"]


def test_a_comparison_in_the_wrong_order_scores_zero():
    cmp = q(kind="comparison", must=[["Voyager 2"]], first=["Voyager 2", "Voyager 1"])
    assert score(cmp, reply("Voyager 2 then Voyager 1."))["correct"]
    r = score(cmp, reply("Voyager 1 then Voyager 2."))
    assert not r["correct"] and not r["order_ok"] and r["score"] == 0.0


def test_a_comparison_naming_only_the_right_candidate_is_in_order():
    cmp = q(kind="comparison", must=[["Voyager 2"]], first=["Voyager 2", "Voyager 1"])
    assert score(cmp, reply("Voyager 2."))["order_ok"]


def test_a_comparison_not_naming_the_right_candidate_is_out_of_order():
    cmp = q(kind="comparison", must=[["Voyager"]], first=["Voyager 2", "Voyager 1"])
    assert not score(cmp, reply("Voyager 1."))["order_ok"]


def test_declining_an_answerable_question_is_a_false_abstention():
    r = score(q(), reply("I can't answer.", abstained=True))
    assert not r["correct"] and r["false_abstention"] and not r["false_answer"]


def test_an_error_on_an_answerable_question_scores_zero_and_is_not_an_abstention():
    r = score(q(), reply("Atlas V", abstained=True, error="boom"))
    assert r["score"] == 0.0 and not r["correct"] and not r["false_abstention"] and r["error"] == "boom"


def test_figures_are_facts_matched_at_the_answers_rounding():
    fig = q(must=[], figures=[{"value": 94_930_000_000}])
    assert score(fig, reply("$94.9 billion"))["correct"]
    assert score(fig, reply("$90 billion"))["missing"] == ["94930000000"]


def test_a_figure_with_a_tolerance_uses_it():
    fig = q(must=[], figures=[{"value": 3e9, "tolerance": 0.1}])
    assert score(fig, reply("about 3.2 billion"))["correct"]


# --- unanswerable questions -----------------------------------------------------------------------

def test_a_cited_hedge_is_a_right_decline():
    r = score(unanswerable(must_not=["Ireland"]), reply("Described as well born [1].", gaps=["birthplace"]))
    assert r["correct"] and r["score"] == 1.0 and not r["false_answer"] and r["missing"] == []


def test_an_invented_fact_is_a_false_answer():
    r = score(unanswerable(must_not=["Ireland"]), reply("Born in Ireland.", gaps=[]))
    assert not r["correct"] and r["false_answer"] and r["forbidden"] == ["Ireland"]


def test_a_decline_that_still_says_a_forbidden_thing_is_a_false_answer():
    r = score(unanswerable(must_not=["Ireland"]), reply("Possibly Ireland, but not stated.", abstained=True))
    assert not r["correct"] and r["false_answer"]


def test_an_error_is_neither_a_right_decline_nor_a_false_answer():
    r = score(unanswerable(), {"error": "down", "abstained": True})
    assert not r["correct"] and not r["false_answer"] and not r["false_abstention"]


# --- grounding, sources, claims -------------------------------------------------------------------

def test_grounded_is_the_share_of_proposed_claims_shown():
    assert score(q(), reply("Atlas V", proposed=4, shown=3))["grounded"] == 0.75
    assert score(q(), reply("Atlas V"))["grounded"] is None
    assert score(q(), reply("Atlas V", proposed=0, shown=0))["grounded"] is None


def test_a_source_hit_accepts_a_file_name_or_a_path_either_way():
    for cited in ("juno.json", "outer-planets/juno.json", "lake/outer-planets/juno.json"):
        assert score(q(sources=["outer-planets/juno.json"]), reply("Atlas V", sources=[{"name": cited}]))["source_hit"], cited


def test_a_source_is_named_by_name_title_or_doc():
    assert score(q(sources=["a.md"]), reply("Atlas V", sources=[{"title": "a.md"}]))["source_hit"]
    assert score(q(sources=["a.md"]), reply("Atlas V", sources=[{"doc": "a.md"}]))["source_hit"]


def test_citation_precision_counts_only_documents():
    r = score(q(sources=["a.md", "b.md"]), reply("Atlas V", sources=[{"name": "a.md"}, {"name": "Mission"}, {"name": "c.md"}]))
    assert r["citation_precision"] == 0.5 and r["citation_recall"] == 0.5


def test_citation_precision_is_unknown_when_no_document_is_cited():
    r = score(q(sources=["a.md"]), reply("Atlas V", sources=[{"name": "Mission"}]))
    assert r["citation_precision"] is None and r["citation_recall"] == 0.0 and r["source_hit"] is False


def test_sources_are_not_scored_without_expected_sources_or_when_abstaining():
    assert score(q(), reply("Atlas V", sources=[{"name": "a.md"}]))["source_hit"] is None
    assert score(q(sources=["a.md"]), reply("", abstained=True, sources=[{"name": "a.md"}]))["source_hit"] is None


def test_claims_count_unless_abstained():
    assert score(q(), reply("Atlas V", claims=[{"text": "a"}, {"text": "b"}]))["claims"] == 2
    assert score(q(), reply("", abstained=True, claims=[{"text": "a"}]))["claims"] == 0


def test_unsupported_claims_come_from_the_verdicts():
    r = score(q(), reply("Atlas V"), verdicts=[{"supported": True}, {"supported": False}, {"supported": False}])
    assert r["unsupported"] == 2 and r["supported_share"] == 0.333


def test_without_a_verifier_unsupported_is_unknown():
    r = score(q(), reply("Atlas V"))
    assert r["unsupported"] is None and r["supported_share"] is None


def test_an_empty_verdict_list_means_no_claim_was_rejected():
    r = score(q(), reply("Atlas V"), verdicts=[])
    assert r["unsupported"] == 0 and r["supported_share"] is None


def test_a_row_carries_the_questions_identity():
    r = score(q(id="q7", kind="list", family="f"), reply("Atlas V"))
    assert (r["id"], r["kind"], r["family"], r["answerable"]) == ("q7", "list", "f", True)


# --- summaries ------------------------------------------------------------------------------------

def test_the_wilson_interval_is_none_for_no_questions():
    assert wilson(0, 0) is None


def test_the_wilson_interval_is_wide_for_small_sets_and_bounded():
    lo, hi = wilson(8, 10)
    assert lo < 0.5 < 0.8 < hi <= 1.0
    assert wilson(10, 10)[1] == 1.0 and wilson(0, 10)[0] == 0.0


def test_the_wilson_interval_narrows_as_the_set_grows():
    small, large = wilson(8, 10), wilson(800, 1000)
    assert large[1] - large[0] < small[1] - small[0]


def row(i, correct, kind="lookup", family="", **kw):
    return {"id": i, "kind": kind, "family": family, "correct": correct, "score": float(correct), "grounded": None,
            "source_hit": None, **kw}


def test_families_report_the_share_answered_alike():
    rows = [row("a", True, family="j"), row("b", False, family="j"), row("c", True, family="d"), row("d", True, family="d")]
    assert families(rows) == {"families": 2, "consistent": 0.5, "split": ["j"]}


def test_a_family_of_one_is_not_a_family():
    assert families([row("a", True, family="j"), row("b", True)]) == {}


def test_a_summary_counts_by_kind_and_overall():
    rows = [row("a", True), row("b", False, kind="list"), row("c", True, kind="list", error="x")]
    s = summarise(rows)
    assert s["all"]["questions"] == 3 and s["all"]["correct"] == 2 and s["all"]["accuracy"] == 0.667
    assert s["list"]["questions"] == 2 and s["all"]["errors"] == 1
    assert "comparison" not in s and "families" not in s


def test_a_summary_counts_false_answers_and_abstentions():
    rows = [row("a", False, false_answer=True), row("b", False, false_abstention=True), row("c", True)]
    s = summarise(rows)["all"]
    assert s["false_answers"] == 1 and s["false_abstentions"] == 1


def test_unsupported_claims_are_summed_only_over_verified_rows():
    rows = [row("a", True, claims=2, unsupported=1, supported_share=0.5), row("b", True, claims=5, unsupported=None)]
    s = summarise(rows)["all"]
    assert s["claims_verified"] == 2 and s["unsupported_claims"] == 1 and s["supported_share"] == 0.5


def test_a_summary_without_verified_rows_leaves_claims_unknown():
    s = summarise([row("a", True)])["all"]
    assert s["claims_verified"] is None and s["unsupported_claims"] is None


def test_means_skip_unknown_values():
    rows = [row("a", True, grounded=1.0, citation_precision=0.5), row("b", True, grounded=None)]
    rows[0]["source_hit"], rows[1]["source_hit"] = True, None
    s = summarise(rows)["all"]
    assert s["grounded"] == 1.0 and s["source_hit_rate"] == 1.0 and s["citation_precision"] == 0.5


def test_an_empty_run_summarises_to_nothing():
    s = summarise([])["all"]
    assert s["questions"] == 0 and s["accuracy"] is None and s["accuracy_ci95"] is None and s["mean_score"] is None
