"""The Gateway tools over a real projection, and the agent's citation check, offline."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from fake_llm import FakeClient
from knowledge_store import collections, layout
from knowledge_store.pipeline import run
from knowledge_store.store import LocalStore, put_json
from knowledge_store.tools import gateway
from test_lifecycle import DOCS, PROFILE


@pytest.fixture
def root(tmp_path):
    root = LocalStore(tmp_path / "root")
    put_json(root, collections.CONFIG, [{"id": "missions"}])
    for n, b in DOCS.items():
        root.put(f"landing/missions/{n}", b.encode())
    lake = collections.scoped(root, "missions")
    put_json(lake, layout.CONFIG_SETTINGS, {"ontology_mode": "auto", "discovery_min_docs": 3, "discovery_resamples": 1})
    put_json(lake, layout.CONFIG_PROFILE, PROFILE.to_dict())
    run.run(root, FakeClient, "fake")
    return root


def ctx(tool: str):
    return SimpleNamespace(client_context=SimpleNamespace(custom={"bedrockAgentCoreToolName": f"knowledge___{tool}"}))


def test_tool_schema_matches_tools():
    names = {t["name"] for t in gateway.tool_schema()}
    assert names == set(gateway.TOOLS)
    for t in gateway.tool_schema():
        assert set(t["inputSchema"]["required"]) <= set(t["inputSchema"]["properties"])


def test_tools_answer_over_the_projection(root, monkeypatch):
    monkeypatch.setattr(gateway, "_lake", root)
    cols = gateway.lambda_handler({}, ctx("list_collections"))
    assert cols["collections"][0]["id"] == "missions" and cols["collections"][0]["ontology_version"] == "0.1.0"
    onto = gateway.lambda_handler({"collection": "missions"}, ctx("describe_ontology"))
    assert "## Types" in onto["ontology"] and onto["version"] == "0.1.0"
    found = gateway.lambda_handler({"collection": "missions", "query": "Nova"}, ctx("search_entities"))
    nova = found["items"][0]
    assert nova["label"] == "Agency Nova" and found["ontology_version"] == "0.1.0"
    ent = gateway.lambda_handler({"collection": "missions", "id": nova["id"]}, ctx("get_entity"))
    assert len(ent["in"]) == 3
    hood = gateway.lambda_handler({"collection": "missions", "id": nova["id"]}, ctx("neighbourhood"))
    assert len(hood["nodes"]) == 4 and len(hood["edges"]) == 3
    pids = ent["passages"][:2]
    read = gateway.lambda_handler({"collection": "missions", "ids": pids}, ctx("read_passages"))
    assert {p["id"] for p in read["passages"]} == set(pids)


def test_tool_errors_are_data(root, monkeypatch):
    monkeypatch.setattr(gateway, "_lake", root)
    assert "no collection" in gateway.lambda_handler({"collection": "nope"}, ctx("get_entity"))["error"]
    assert "unknown tool" in gateway.lambda_handler({}, ctx("drop_tables"))["error"]
