"""The Azure host: token verification, the portal API and MCP behind it, the chat and upload
queues, and the Terraform root's wiring. Tokens are signed here with a key made for the test,
so every check authn.py makes is exercised."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import pytest

from knowledge_store import authn
from knowledge_store.hosts import azure as host
from knowledge_store.portal_api import handler, index
from knowledge_store.portal_api.state import MemoryState
from test_review_fixes import mixed  # noqa: F401  (fixture: a collection with public and private sources)

ROOT = Path(__file__).resolve().parents[1]
TENANT = "00000000-0000-0000-0000-00000000000a"
API = "11111111-1111-1111-1111-11111111111b"
ISSUER = f"https://login.microsoftonline.com/{TENANT}/v2.0"


@pytest.fixture(scope="module")
def key():
    from cryptography.hazmat.primitives.asymmetric import rsa
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def entra(key, monkeypatch):
    """Entra's token shape and this deployment's claim settings, with the test key as the JWKS."""
    class Keys:
        def get_signing_key_from_jwt(self, token):
            return type("K", (), {"key": key.public_key()})()

    monkeypatch.setattr(authn, "_keys", lambda url: Keys())
    for k, v in {"AUTH_ISSUERS": ISSUER, "AUTH_AUDIENCES": f"{API},api://{API}", "AUTH_JWKS_URL": "https://keys",
                 "SUBJECT_CLAIM": "oid,sub", "GROUPS_CLAIM": "roles", "PRIVATE_GROUP": "private-reader",
                 "SCOPES_CLAIM": "roles", "PRIVATE_SCOPE": "tools.private"}.items():
        monkeypatch.setenv(k, v)

    def token(**over):
        import jwt
        now = int(time.time())
        claims = {"iss": ISSUER, "aud": API, "oid": "person-1", "sub": "pairwise", "iat": now, "nbf": now,
                  "exp": now + 600, **over}
        return jwt.encode({k: v for k, v in claims.items() if v is not None}, key, algorithm="RS256", headers={"kid": "k1"})
    return token


# --- authn ---------------------------------------------------------------------------------------


def test_authn_accepts_only_valid_tokens(entra, key):
    assert authn.verify(entra())["oid"] == "person-1"
    assert authn.verify(entra(aud=f"api://{API}"))["oid"] == "person-1"
    for bad in (entra(exp=int(time.time()) - 3600), entra(aud="someone-else"), entra(iss="https://evil/v2.0"),
                entra(exp=None)):
        with pytest.raises(authn.Unauthorized):
            authn.verify(bad)
    from cryptography.hazmat.primitives.asymmetric import rsa
    import jwt
    forged = jwt.encode({"iss": ISSUER, "aud": API, "exp": int(time.time()) + 600},
                        rsa.generate_private_key(public_exponent=65537, key_size=2048), algorithm="RS256")
    with pytest.raises(authn.Unauthorized):
        authn.verify(forged)
    with pytest.raises(authn.Unauthorized):
        authn.bearer("Basic abc")


# --- the portal API and MCP, as the Function App calls them ------------------------------------------


@pytest.fixture
def served(mixed, entra, monkeypatch):
    root, _ = mixed
    monkeypatch.setattr(handler, "_lake", root)
    monkeypatch.setattr(handler, "_state", MemoryState())
    index._cache.clear()
    return entra


def _portal(token, path, qs=None, method="GET", body=None):
    headers = {"authorization": f"Bearer {token}"} if token else {}
    status, _, out = host.portal(method, path, {"c": "m", **(qs or {})}, body, headers)
    return status, json.loads(out)


def test_portal_needs_a_token_and_scopes_by_role(served):
    assert _portal(None, "/api/collections")[0] == 401
    assert _portal("not-a-jwt", "/api/collections")[0] == 401
    assert _portal(served(), "/api/entities", {"q": "Zeta"})[1]["total"] == 0
    assert _portal(served(roles=["private-reader"]), "/api/entities", {"q": "Zeta"})[1]["total"] == 1
    # an application granted tools.private is not a private reader of the portal
    assert _portal(served(roles=["tools.private"]), "/api/entities", {"q": "Zeta"})[1]["total"] == 0


def test_portal_chat_goes_to_the_queue(served, monkeypatch):
    sent = []
    monkeypatch.setattr(host, "send_chat", lambda job, context=None: sent.append(job))
    status, body = _portal(served(), "/api/chat", method="POST", body=json.dumps({"question": "Who launched Alpha?"}))
    assert status == 202 and sent[0]["id"] == body["id"] and sent[0]["sub"] == "person-1" and sent[0]["private"] is False
    status, body = _portal(served(), "/api/chat", {"id": body["id"]})
    assert status == 200 and body["status"] == "pending"
    assert _portal(served(oid="someone-else"), "/api/chat", {"id": sent[0]["id"]})[0] == 404


def _mcp(token, message, method="POST"):
    headers = {"authorization": f"Bearer {token}"} if token else {}
    status, _, out = host.mcp(method, json.dumps(message) if not isinstance(message, str) else message, headers)
    return status, (json.loads(out) if out else None)


def test_mcp_lists_and_calls_tools_in_the_callers_scope(served):
    status, init = _mcp(served(), {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                                   "params": {"protocolVersion": "2025-06-18", "capabilities": {}}})
    assert status == 200 and init["result"]["protocolVersion"] == "2025-06-18"
    assert _mcp(served(), {"jsonrpc": "2.0", "method": "notifications/initialized"}) == (202, None)
    tools = _mcp(served(), {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})[1]["result"]["tools"]
    assert {"find_paths", "neighbourhood", "search_entities"} <= {t["name"] for t in tools}
    assert all("caller_private" not in t["inputSchema"]["properties"] for t in tools)

    def search(token, extra=None):
        args = {"collection": "m", "query": "Zeta", **(extra or {})}
        out = _mcp(token, {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                           "params": {"name": "search_entities", "arguments": args}})[1]["result"]
        return out["structuredContent"]["total"]
    assert search(served(), {"caller_private": True}) == 0  # the model cannot widen its scope
    assert search(served(roles=["tools.private"])) == 1
    assert search(served(roles=["private-reader"])) == 1
    paths = _mcp(served(), {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "find_paths", "arguments": {
        "collection": "m", "from": "entity/Mission/mission-alpha", "to": "entity/SpaceAgency/agency-orbis"}}})[1]
    assert paths["result"]["structuredContent"]["hops"] == 3


def test_mcp_refuses_what_it_should(served):
    assert _mcp(None, {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})[0] == 401
    assert _mcp(served(), {}, method="GET")[0] == 405
    assert _mcp(served(), "{not json")[0] == 400
    assert _mcp(served(), {"jsonrpc": "2.0", "id": 1, "method": "resources/list"})[1]["error"]["code"] == -32601
    assert _mcp(served(), {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "drop_everything"}})[1]["error"]["code"] == -32602


# --- queues --------------------------------------------------------------------------------------


def test_drain_deletes_every_notification(monkeypatch):
    class Queue:
        def __init__(self):
            self.messages, self.deleted = [object() for _ in range(70)], []

        def receive_messages(self, messages_per_page, visibility_timeout):
            yield from list(self.messages)

        def delete_message(self, m):
            self.deleted.append(m)

    q = Queue()
    monkeypatch.setattr(host, "_queue", lambda name: q)
    assert host.drain() == 70 and len(q.deleted) == 70


def test_answer_drops_what_is_not_a_job(monkeypatch):
    called = []
    monkeypatch.setattr(handler, "answer_job", lambda job: called.append(job))
    host.answer("not json")
    host.answer(json.dumps({"something": "else"}))
    host.answer(json.dumps({"chat_job": {"id": "x"}}))
    assert called == [{"id": "x"}]


# --- Terraform -----------------------------------------------------------------------------------


def _variables(path: Path) -> set[str]:
    return set(re.findall(r'^variable "([^"]+)"', "".join(p.read_text() for p in path.glob("*.tf")), re.M))


def test_azure_stack_root_passes_every_module_input():
    module = _variables(ROOT / "infra/azure/modules/knowledge-store")
    stack = (ROOT / "infra/azure/stack/main.tf").read_text()
    passed = set(re.findall(r"^\s+(\w+)\s+= var\.\1$", stack, re.M))
    assert module == passed
    assert module | {"subscription_id"} == _variables(ROOT / "infra/azure/stack")


def test_function_app_registers_its_functions():
    pytest.importorskip("azure.functions")
    import importlib.util
    spec = importlib.util.spec_from_file_location("function_app", ROOT / "functions/azure/function_app.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    names = {f.get_function_name() for f in mod.app.get_functions()}
    assert names == {"portal", "mcp", "chat"}
