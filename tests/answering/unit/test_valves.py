"""Valves: the limits around a question, and the catalog questions a mapped table answers."""

from __future__ import annotations

from knowledge_store.answering.domain import valves

MISSION = {"type": "Mission", "columns": [{"attribute": "sampleCost"}, {"attribute": "vehicleFamily"}]}


def test_a_limit_comes_from_its_setting(monkeypatch):
    monkeypatch.setenv("MAX_TOOL_CALLS", "3")
    assert valves.limit("MAX_TOOL_CALLS", 16) == 3


def test_a_limit_that_is_not_a_number_falls_back_to_its_default(monkeypatch):
    monkeypatch.setenv("MAX_TOOL_CALLS", "many")
    assert valves.limit("MAX_TOOL_CALLS", 16) == 16


def test_an_unset_limit_is_its_default(monkeypatch):
    monkeypatch.delenv("MAX_TOOL_CALLS", raising=False)
    assert valves.limit("MAX_TOOL_CALLS", 16) == 16


def test_the_default_limits_are_positive():
    for n in (valves.MAX_QUESTION_CHARS, valves.MAX_HISTORY_TURNS, valves.MAX_TOOL_CALLS, valves.MAX_MODEL_CALLS,
              valves.MAX_OUTPUT_TOKENS):
        assert n > 0
    assert valves.GROUNDING_REPAIRS >= 0


def test_a_collection_with_no_mapping_gets_no_table_questions():
    assert valves.table_questions(None) == ()
    assert valves.table_questions("not a description") == ()
    assert valves.table_questions({}) == ()


def test_a_question_is_offered_only_when_every_attribute_it_needs_is_mapped():
    only_cost = {"types": [{"type": "Mission", "columns": [{"attribute": "sampleCost"}]}]}
    qs = valves.table_questions(only_cost)
    assert "What sample cost does the catalog give Juno?" in qs
    assert "What total sample cost does the catalog give the Atlas V missions?" not in qs


def test_both_attributes_mapped_offers_the_combined_question():
    qs = valves.table_questions({"types": [MISSION]})
    assert "What total sample cost does the catalog give the Atlas V missions?" in qs
    assert "Which missions launched on an Atlas V?" in qs


def test_an_attribute_on_another_type_does_not_count():
    qs = valves.table_questions({"types": [{"type": "LaunchVehicle", "columns": [{"attribute": "sampleCost"}]}]})
    assert "What sample cost does the catalog give Juno?" not in qs


def test_a_metric_question_needs_the_metric_published():
    assert "How many catalogued missions launched on an Atlas V?" in valves.table_questions(
        {"metrics": [{"name": "atlas_v_launches"}]})
    assert valves.table_questions({"metrics": [{"name": "other"}, "junk", {}]}) == ()


def test_columns_without_an_attribute_or_types_without_a_name_are_ignored():
    assert valves.table_questions({"types": [{"columns": [{"attribute": "name"}]}, {"type": "LaunchVehicle", "columns": [{}]}]}) == ()


def test_the_note_lists_each_question():
    note = valves.table_query_note(("Q1?", "Q2?"))
    assert note.endswith("figure:\n- Q1?\n- Q2?")


def test_no_questions_means_no_note():
    assert valves.table_query_note(()) == ""
