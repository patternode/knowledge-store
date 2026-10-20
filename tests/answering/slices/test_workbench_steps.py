"""The workbench slice without a collection: step titles, sources, reports, usage totals and prices."""

from __future__ import annotations

import datetime as dt

import pytest

from knowledge_store.answering.slices import workbench as wb

SONNET = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"


@pytest.mark.parametrize("name, out, source", [
    ("get_entity", {}, "graph"),
    ("aggregate", {}, "structured"),
    ("search_passages", {"method": "vector"}, "vector"),
    ("search_passages", {}, "keyword"),
    ("read_passages", {}, None),
])
def test_each_tool_names_where_it_looked(name, out, source):
    assert wb.query_source(name, out) == source


def test_a_gateway_tool_name_loses_its_target():
    assert wb.bare("kg___get_entity") == "get_entity"
    assert wb.bare("get_entity") == "get_entity"
    assert wb.bare(None) == ""


@pytest.mark.parametrize("name, args, out, title, count", [
    ("describe_ontology", {}, {"version": "v3"}, "Read the ontology (version v3)", None),
    ("list_collections", {}, {"collections": [1, 2]}, "Listed the collections", 2),
    ("list_entities", {"type": "Mission"}, {"items": [{"label": "A"}]}, "Listed entities of type Mission: 1", 1),
    ("get_entity", {"id": "e1"}, {"label": "Alpha", "attributes": [1], "out": [1, 2], "in": []}, "Read Alpha: 3 facts", 3),
    ("neighbourhood", {"id": "e1", "hops": 2}, {"nodes": [1, 2, 3]}, "Explored around e1 (2 hops): 3 entities", 3),
    ("find_paths", {"from": "a", "to": "b"}, {"paths": [1]}, "Looked for paths from a to b: 1 found", 1),
    ("search_passages", {"query": "q"}, {"passages": [{"title": "T"}], "method": "vector"},
     "Vector search of passages for “q”: 1 found", 1),
    ("read_passages", {}, {"passages": [1]}, "Read 1 passage", 1),
    ("read_passages", {}, {"passages": [1, 2]}, "Read 2 passages", 2),
    ("describe_structured", {}, {"types": [1]}, "Read the mapped tables: 1", 1),
    ("lookup_rows", {}, {"type": "Mission", "rows": [1, 2]}, "Looked up Mission: 2", 2),
    ("lookup_rows", {}, {"cells": [1]}, "Looked up cells: 1", 1),
    ("aggregate", {}, {"metric": "launches", "figure": 3}, "Structured lookup: launches = 3", None),
    ("mystery", {}, {}, "Called mystery", None),
])
def test_each_tool_call_reads_as_a_title_and_a_count(name, args, out, title, count):
    got_title, _, got_count = wb.describe(name, args, out)
    assert got_title == title and got_count == count


def test_a_failed_tool_call_says_so_with_its_error():
    assert wb.describe("get_entity", {}, {"error": "no such entity"}) == ("get_entity failed", "no such entity", None)


def test_a_long_label_is_shortened_with_an_ellipsis():
    title, _, _ = wb.describe("search_entities", {"query": "x" * 100}, {"items": [], "total": 0})
    assert "…" in title and len(title) < 120


def test_a_tool_result_from_an_agent_framework_is_parsed_from_its_text_block():
    rec = wb.Recorder()
    step = rec.tool("read_passages", {}, {"toolUseId": "t", "content": [{"text": '{"passages": [{"id": "p1"}]}'}]})
    assert step["count"] == 1


def test_a_tool_result_whose_text_is_not_json_is_its_error():
    rec = wb.Recorder()
    step = rec.tool("read_passages", {}, {"toolUseId": "t", "content": [{"text": "boom"}]})
    assert step["error"] == "boom" and step["title"] == "read_passages failed"


def test_a_tool_result_that_is_a_json_list_is_wrapped():
    rec = wb.Recorder()
    step = rec.tool("list_collections", {}, {"toolUseId": "t", "content": [{"text": "[1, 2]"}]})
    assert step["count"] == 0  # a list is not a collections result


def test_a_reporter_that_raises_does_not_break_the_question():
    def broken(_):
        raise RuntimeError("socket closed")
    rec = wb.Recorder(broken)
    rec.step("tool", "Read something")
    assert rec.steps[0]["title"] == "Read something"


def test_structured_tools_record_the_type_attributes_and_filters_they_queried():
    rec = wb.Recorder()
    rec.tool("aggregate", {"type": "Mission", "attribute": "cost", "group_by": "agency",
                           "filters": [{"attribute": "vehicleFamily"}, "junk"]}, {"rows": [{"type": "Mission"}]})
    hits = rec.hits()
    assert hits["classes"]["Mission"] == ["queried", "read"]
    assert set(hits["attributes"]) == {"cost", "agency", "vehicleFamily"}


def test_a_failed_graph_call_touches_no_terms():
    rec = wb.Recorder()
    rec.tool("search_entities", {"type": "Mission"}, {"error": "down"})
    assert rec.hits() == {}


def test_a_path_records_the_types_and_relations_along_it():
    rec = wb.Recorder()
    rec.tool("find_paths", {"from": "a", "to": "b"},
             {"paths": [{"nodes": [{"type": "Mission"}, {"type": "Agency"}], "edges": [{"p": "launchedBy"}]}]})
    hits = rec.hits()
    assert set(hits["classes"]) == {"Mission", "Agency"} and hits["relations"] == {"launchedBy": ["read"]}


def test_backfill_records_the_tool_calls_of_a_finished_conversation():
    rec = wb.Recorder()
    rec.backfill([{"content": [{"toolUse": {"toolUseId": "1", "name": "kg___read_passages", "input": {"ids": ["p1"]}}}]},
                  {"content": [{"toolResult": {"toolUseId": "1", "content": [{"text": '{"passages": [{}]}'}]}}, "text"]}])
    assert [s["tool"] for s in rec.steps] == ["read_passages"] and rec.tool_calls == 1


def test_backfill_does_nothing_when_hooks_reported_live():
    rec = wb.Recorder()
    rec.live = True
    rec.backfill([{"content": [{"toolUse": {"toolUseId": "1", "name": "x", "input": {}}}]}])
    assert rec.steps == []


def test_pricing_without_a_model_step_does_nothing():
    rec = wb.Recorder()
    rec.price_model({"inputTokens": 1}, SONNET)
    assert rec.steps == []


# --- what a question cost ---------------------------------------------------------------------

def test_nothing_reported_means_no_price():
    assert wb.query_cost([{"kind": "model"}], model_id=SONNET) is None


def test_the_price_comes_from_per_call_usage():
    steps = [{"kind": "model", "n": 1, "title": "Thinking", "usage": {"inputTokens": 1000, "outputTokens": 100}, "usd": 0.1},
             {"kind": "tool", "n": 2}]
    cost = wb.query_cost(steps, model_id=SONNET)
    assert cost["priced"] and cost["usd"] > 0
    assert cost["calls"] == [{"n": 1, "title": "Thinking", "usd": 0.1, "tokens": 1100}]
    assert "omitted" not in cost


def test_the_larger_of_the_per_call_and_the_whole_usage_is_priced():
    steps = [{"kind": "model", "usage": {"inputTokens": 10}}]
    small = wb.query_cost(steps, model_id=SONNET)
    large = wb.query_cost(steps, model_id=SONNET, usage={"inputTokens": 10000})
    assert large["usd"] > small["usd"]


def test_the_whole_usage_alone_is_priced_when_no_call_reported():
    assert wb.query_cost([], model_id=SONNET, usage={"inputTokens": 1000})["priced"]


def test_an_unknown_model_lists_the_tokens_without_a_price():
    cost = wb.query_cost([], model_id="no-such-model", usage={"inputTokens": 5})
    assert cost["priced"] is False and cost["usd"] is None
    assert any(p["tokens"] == 5 for p in cost["parts"])


def test_a_guardrail_check_is_named_as_left_out_of_the_price():
    cost = wb.query_cost([{"kind": "guardrail"}], model_id=SONNET, usage={"inputTokens": 1})
    assert cost["omitted"] == "The guardrail check is not in this price."


# --- usage totals -------------------------------------------------------------------------------

def test_hits_become_counters_and_back():
    hits = {"classes": {"Mission": ["queried", "read"]}, "relations": {"launchedBy": ["cited"]},
            "other": {"x": ["read"]}, "attributes": {"cost": ["bogus"]}}
    counters = wb.usage_counts(hits)
    assert counters == {"classes|Mission|queried": 1, "classes|Mission|read": 1, "relations|launchedBy|cited": 1}
    view = wb.usage_view({**counters, "questions": 4, "junk": 1, "classes|Mission|nope": 2})
    assert view["questions"] == 4
    assert view["classes"]["Mission"] == {"queried": 1, "read": 1, "cited": 0}
    assert view["attributes"] == {}


def test_no_hits_count_nothing():
    assert wb.usage_counts(None) == {}


def test_the_month_bucket_is_year_and_month():
    assert wb.month(dt.datetime(2026, 3, 9, tzinfo=dt.timezone.utc)) == "2026-03"
    assert len(wb.month()) == 7


# --- reports and requests -----------------------------------------------------------------------

def test_a_report_is_cleaned_to_the_schema_whatever_the_model_sent():
    r = wb.clean_report({"verdict": "maybe", "summary": "s" * 2000, "extra": 1,
                         "ontology": {"classes": [{"name": "Rocket", "definition": "d", "colour": "red"}, {"definition": "no name"}, "x"]},
                         "existing": [{"term": "Mission", "kind": "class"}],
                         "rewrites": ["Q?", "", 3, "R?", "S?", "T?", "U?", "V?"]})
    assert r["verdict"] == "data_missing"
    assert len(r["summary"]) == 1500
    assert r["ontology"]["classes"] == [{"name": "Rocket", "definition": "d"}]
    assert r["ontology"]["relations"] == [] and r["data"] == []
    assert r["rewrites"] == ["Q?", "R?", "S?"]  # the first five, less the blank and the non-text
    assert "extra" not in r


def test_a_report_that_is_not_an_object_is_an_empty_one():
    assert wb.clean_report(None)["verdict"] == "data_missing"


def test_a_kept_request_is_keyed_by_time_under_the_requests_folder():
    now = dt.datetime(2026, 10, 20, 9, 30, tzinfo=dt.timezone.utc)
    key, body = wb.request_record("Q" * 3000, {"verdict": "ontology_missing", "summary": "s"}, version="v2", by="u", now=now)
    assert key.startswith(f"{wb.REQUESTS}/20261020T093000-") and key.endswith(".json")
    assert body["at"] == "2026-10-20T09:30:00+00:00" and len(body["question"]) == 2000
    assert body["report"]["verdict"] == "ontology_missing" and body["ontology_version"] == "v2"


def test_the_analyst_is_told_what_the_chat_agent_found():
    p = wb.analyst_prompt("Who built it?", {"answer": "I can't say.", "gaps": ["the builder"], "steps": ["Searched"]})
    assert p.startswith("The question: Who built it?")
    assert "The chat agent's answer was: I can't say." in p
    assert "do not cover: the builder" in p and "- Searched" in p


def test_the_analyst_prompt_without_findings_is_the_question():
    assert wb.analyst_prompt("Q?", None) == "The question: Q?"


def test_the_report_schema_offers_every_verdict():
    assert wb.REPORT_SCHEMA["properties"]["verdict"]["enum"] == list(wb.VERDICTS)
