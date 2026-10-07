"""The agent's scope path: the interceptor sets caller_private from the verified token, overwriting
whatever the model sent; the tools honour it; the committed Gateway schema matches the code."""

from __future__ import annotations

import base64
import json

import pytest
from pathlib import Path
from types import SimpleNamespace

from knowledge_store.tools import gateway, interceptor
from test_review_fixes import mixed  # noqa: F401  (fixture: a collection with public and private sources)

ROOT = Path(__file__).resolve().parents[1]


def token(claims: dict) -> str:
    enc = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")  # noqa: E731
    return f"{enc({'alg': 'none'})}.{enc(claims)}.sig"


def intercept(claims: dict, arguments: dict) -> dict:
    event = {"interceptorInputVersion": "1.0", "mcp": {"gatewayRequest": {
        "headers": {"Authorization": f"Bearer {token(claims)}"},
        "body": {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                 "params": {"name": "knowledge___get_entity", "arguments": dict(arguments)}}}}}
    out = interceptor.lambda_handler(event, None)
    return out["mcp"]["transformedGatewayRequest"]["body"]["params"]["arguments"]


def test_interceptor_derives_scope_and_overrides_the_model():
    assert intercept({"sub": "u", "cognito:groups": ["private-readers"]}, {})["caller_private"] is True
    assert intercept({"sub": "u", "cognito:groups": ["readers"]}, {"caller_private": True})["caller_private"] is False
    assert intercept({"client_id": "app", "scope": "knowledge-store/agent.invoke knowledge-store/tools.private"}, {})["caller_private"] is True
    assert intercept({"client_id": "app", "scope": "knowledge-store/tools.public"}, {"caller_private": True})["caller_private"] is False
    assert intercept({}, {"collection": "m"}) == {"collection": "m", "caller_private": False}


def test_interceptor_leaves_other_methods_alone():
    event = {"mcp": {"gatewayRequest": {"headers": {}, "body": {"method": "tools/list", "params": {}}}}}
    body = interceptor.lambda_handler(event, None)["mcp"]["transformedGatewayRequest"]["body"]
    assert body == {"method": "tools/list", "params": {}}


def test_tools_honour_the_injected_scope(mixed, monkeypatch):  # noqa: F811
    root, _ = mixed
    monkeypatch.setattr(gateway, "_lake", root)
    ctx = SimpleNamespace(client_context=SimpleNamespace(custom={"bedrockAgentCoreToolName": "knowledge___search_entities"}))
    public = gateway.lambda_handler({"collection": "m", "query": "Zeta", "caller_private": False}, ctx)
    private = gateway.lambda_handler({"collection": "m", "query": "Zeta", "caller_private": True}, ctx)
    absent = gateway.lambda_handler({"collection": "m", "query": "Zeta"}, ctx)
    assert public["total"] == 0 and absent["total"] == 0 and private["total"] == 1
    # only a real boolean true opens private scope
    assert gateway.lambda_handler({"collection": "m", "query": "Zeta", "caller_private": "true"}, ctx)["total"] == 0


@pytest.mark.parametrize("name,toolset", [("schema.json", "all"), ("schema-graph.json", "graph"),
                                          ("schema-passages.json", "passages")])
def test_committed_tool_schemas_match_the_code(name, toolset):
    committed = json.loads((ROOT / "src/knowledge_store/tools" / name).read_text())
    assert committed == gateway.tool_schema(toolset), f"regenerate src/knowledge_store/tools/{name} from tool_schema()"
    for t in committed:
        assert "caller_private" in t["inputSchema"]["properties"], "the interceptor sets a declared input"
