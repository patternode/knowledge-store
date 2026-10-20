"""The Gateway REQUEST interceptor: every tool call carries whether its caller may read private content."""

from __future__ import annotations

import base64
import json

import pytest

from knowledge_store.access.adapters import gateway_interceptor as gi


@pytest.fixture(autouse=True)
def cognito(monkeypatch):
    for var in ("GROUPS_CLAIM", "PRIVATE_GROUP", "SCOPES_CLAIM", "PRIVATE_SCOPE", "SCOPE_PREFIX"):
        monkeypatch.delenv(var, raising=False)


def jwt(claims: dict) -> str:
    body = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return f"h.{body}.sig"


def event(body, authorization=None):
    headers = {"Authorization": authorization} if authorization else {}
    return {"mcp": {"gatewayRequest": {"headers": headers, "body": body}}}


def call(name="search_entities", args=None):
    return {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": args or {}}}


def args_of(out):
    assert out["interceptorOutputVersion"] == "1.0"
    return out["mcp"]["transformedGatewayRequest"]["body"]["params"]["arguments"]


def test_a_private_reader_is_marked_private():
    out = gi.lambda_handler(event(call(), "Bearer " + jwt({"cognito:groups": ["private-readers"]})), None)
    assert args_of(out)["caller_private"] is True


def test_a_public_reader_is_marked_public():
    out = gi.lambda_handler(event(call(), "Bearer " + jwt({"cognito:groups": ["readers"]})), None)
    assert args_of(out)["caller_private"] is False


def test_an_application_with_the_private_scope_is_marked_private():
    out = gi.lambda_handler(event(call(), jwt({"scope": "knowledge-store/tools.private"})), None)
    assert args_of(out)["caller_private"] is True


def test_what_the_model_or_caller_put_in_the_argument_is_overwritten():
    out = gi.lambda_handler(event(call(args={"caller_private": True, "query": "x"}), "Bearer " + jwt({})), None)
    assert args_of(out) == {"caller_private": False, "query": "x"}


def test_a_request_without_a_token_is_public():
    assert args_of(gi.lambda_handler(event(call()), None))["caller_private"] is False


def test_a_body_sent_as_text_is_parsed():
    out = gi.lambda_handler(event(json.dumps(call()), "Bearer " + jwt({"cognito:groups": "[private-readers]"})), None)
    assert args_of(out)["caller_private"] is True


def test_a_call_without_arguments_gets_them():
    body = {"method": "tools/call"}
    out = gi.lambda_handler(event(body, None), None)
    assert args_of(out) == {"caller_private": False}


def test_requests_other_than_tool_calls_pass_unchanged():
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    out = gi.lambda_handler(event(dict(body)), None)
    assert out["mcp"]["transformedGatewayRequest"]["body"] == body


def test_an_empty_event_passes_through():
    assert gi.lambda_handler({}, None)["mcp"]["transformedGatewayRequest"]["body"] == {}


@pytest.mark.parametrize("header", [None, "", "Bearer", "Bearer not-a-jwt", "Bearer a.%%%.c"])
def test_a_token_that_cannot_be_read_has_no_claims(header):
    assert gi.claims_of(header) == {}


def test_claims_are_read_with_or_without_the_bearer_prefix():
    token = jwt({"sub": "u"})
    assert gi.claims_of(token) == gi.claims_of("bearer " + token) == {"sub": "u"}
