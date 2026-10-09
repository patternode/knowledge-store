"""The valves name the catalog questions a mapped table answers, and a claim from one of them
is grounded against the cell or the figure."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("pydantic")

from knowledge_store.agent import app, valves  # noqa: E402
from knowledge_store.agent.grounding import Citation, Claim, GroundedAnswer  # noqa: E402
from knowledge_store.config import SourceConfig  # noqa: E402
from knowledge_store.ontology import versions  # noqa: E402
from knowledge_store.pipeline.ingest import ingest_source  # noqa: E402
from knowledge_store.structured.bind import bind  # noqa: E402
from knowledge_store.structured.query import aggregate, describe, lookup_rows  # noqa: E402
from knowledge_store.tools import gateway  # noqa: E402
from test_structured import CORPUS, ONTO, _collection  # noqa: E402


class Tools:
    def __init__(self, root):
        self.root = root

    def call(self, name, args):
        return gateway.call(self.root, name, args)


class Scripted:
    def __init__(self, answer):
        self.answer, self.prompts, self.messages = answer, [], []

    def __call__(self, prompt):
        self.prompts.append(prompt)
        return SimpleNamespace(structured_output=self.answer)


class RecordingGuardrail:
    def __init__(self):
        self.calls = []

    def question(self, text):
        return None

    def grounded(self, question, claim, sources):
        self.calls.append((question, claim, list(sources)))
        return True, 0.9


def _bound(tmp_path):
    root, lake = _collection(tmp_path)
    versions.publish(lake, ONTO, by="test", activate=True)
    ingest_source(lake, SourceConfig("missions-tables", "local_dir",
                                     {"path": str(CORPUS), "pattern": "tables/*.csv"}))
    assert bind(lake)["misses"] == []
    return root, lake


def test_the_catalog_questions_are_the_valve_list():
    assert [q.question for q in valves.TABLE_QUERIES] == [
        "What sample cost does the catalog give Juno?",
        "Which missions launched on an Atlas V?",
        "How many catalogued missions launched on an Atlas V?",
        "What total sample cost does the catalog give the Atlas V missions?",
        "What name does the catalog give the launch vehicle atlas-v-551?",
    ]
    assert "cells and figures" in valves.TOOL_BUDGET_SPENT


def test_a_collection_without_those_columns_is_not_given_the_catalog_questions():
    assert valves.table_questions(None) == ()
    assert valves.table_questions({"types": [], "metrics": []}) == ()
    banking = {"types": [{"type": "Account", "columns": [{"attribute": "balance"}]}], "metrics": []}
    assert valves.table_questions(banking) == ()
    assert valves.table_query_note(()) == ""


def test_the_bound_catalog_adds_every_table_question_to_the_prompt(tmp_path):
    _, lake = _bound(tmp_path)
    questions = valves.table_questions(describe(lake))
    assert questions == tuple(q.question for q in valves.TABLE_QUERIES)
    prompt = app.prompt_for("missions", "1.0.0", "ontology", describe(lake))
    for question in questions:
        assert question in prompt
    assert "Cite each value as its cell" in prompt
    bare = app.prompt_for("missions", "1.0.0", "ontology", {"types": [], "metrics": []})
    assert "Juno" not in bare

    from types import SimpleNamespace as NS
    from knowledge_store.portal_api.chat import system_text
    idx = NS(lake=lake, ontology={"classes": [], "relations": [], "attributes": []},
             summary={"profile": {"name": "Missions", "description": "A catalog."}})
    portal = system_text(idx)
    for question in questions:
        assert question in portal


def test_a_table_query_is_grounded_against_the_cell_or_the_figure(tmp_path):
    root, lake = _bound(tmp_path)
    cost = lookup_rows(lake, "Mission", [{"attribute": "name", "op": "eq", "value": "Juno"}])
    cell = cost["rows"][0]["values"]["sampleCostMillionUsd"]
    question = valves.TABLE_QUERIES[0].question
    guard = RecordingGuardrail()
    stated = GroundedAnswer(answerable=True, claims=[Claim(
        text="The catalog gives Juno a sample cost of 1100.",
        citations=[Citation(cell_id=cell["cell"], value="1100")])])
    out = app.answer(question, "missions", None, Tools(root), guardrail=guard, agent_factory=lambda: Scripted(stated))
    assert not out["abstained"] and out["sources"][0]["kind"] == "cell"
    assert guard.calls == [(question, stated.claims[0].text, ["sample_cost_million_usd: 1100"])]
    assert any(s["kind"] == "tool" and s.get("tool") == "describe_structured" for s in out["steps"])

    figure = aggregate(lake, metric="atlas_v_launches")
    count_q = valves.TABLE_QUERIES[2].question
    guard = RecordingGuardrail()
    counted = GroundedAnswer(answerable=True, claims=[Claim(
        text="Five catalogued missions launched on an Atlas V.",
        citations=[Citation(metric_id=figure["id"], figure="5")])])
    out = app.answer(count_q, "missions", None, Tools(root), guardrail=guard, agent_factory=lambda: Scripted(counted))
    assert not out["abstained"] and out["sources"][0]["kind"] == "metric"
    assert guard.calls == [(count_q, counted.claims[0].text, ["5"])]
