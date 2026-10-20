"""The portal API's input and output hardening: numeric parameters, bounded history and requests,
generic errors, labels in scope, and the local server's Host, Origin and CORS handling."""

from __future__ import annotations

import io
import json
import urllib.error

import pytest

from knowledge_store.answering.domain import valves
from knowledge_store.answering.adapters import agent_client
from knowledge_store.answering.slices import chat
from knowledge_store.access.adapters import portal as handler
from knowledge_store.knowledge_graph.adapters import index
from knowledge_store.apps import local_portal as local
from test_chat_api import State, event
from test_review_fixes import _call, mixed  # noqa: F401


# -- numeric query parameters -----------------------------------------------------------------

def test_number_parses_clamps_and_refuses():
    assert handler.number({}, "limit", 50, 1, 200) == 50
    assert handler.number({"limit": "999"}, "limit", 50, 1, 200) == 200
    assert handler.number({"offset": "-5"}, "offset", 0, 0, 10) == 0
    for bad in ("abc", "1.5", "1e3"):
        with pytest.raises(handler.BadRequest):
            handler.number({"limit": bad}, "limit", 50, 1, 200)


@pytest.mark.parametrize("path,qs", [("/api/entities", {"limit": "x"}), ("/api/entities", {"offset": "nope"}),
                                     ("/api/graph", {"limit": "1;"}), ("/api/neighbourhood", {"hops": "two"}),
                                     ("/api/paths", {"hops": "", "limit": "ten"})])
def test_malformed_numbers_are_400s(mixed, path, qs):
    status, body = _call(path, private=True, qs=qs)
    assert status == 400 and "integer" in body["error"]


def test_negative_offset_is_clamped(mixed, monkeypatch):
    seen = {}
    real = index.Index.search_entities
    monkeypatch.setattr(index.Index, "search_entities",
                        lambda self, *a, **k: seen.update(k) or real(self, *a, **k))
    status, _ = _call("/api/entities", private=True, qs={"offset": "-10", "limit": "-3"})
    assert status == 200 and seen["offset"] == 0 and seen["limit"] == 1


def test_entity_search_is_capped(mixed):
    assert _call("/api/entities", private=True, qs={"q": "x" * 201})[0] == 400
    assert _call("/api/entities", private=True, qs={"q": "x" * 200})[0] == 200


# -- chat history -------------------------------------------------------------------------------

def test_history_is_strings_and_bounded():
    big = {"q": "q" * 10_000, "a": "a" * 10_000}
    h = handler.history_of({"history": [{"q": 1, "a": "x"}, {"q": "x", "a": {"x": 1}}, "junk", {"q": "", "a": "x"}, big]})
    assert h == [{"q": "q" * valves.MAX_QUESTION_CHARS, "a": "a" * handler.MAX_ANSWER_CHARS}]
    assert len(handler.history_of({"history": [{"q": "q", "a": "a"}] * 50})) == valves.MAX_HISTORY_TURNS
    assert handler.history_of({"history": "not a list"}) == []


def test_chat_job_carries_bounded_history(mixed, monkeypatch):
    sent = []
    monkeypatch.setattr(handler, "_state", State())
    monkeypatch.setattr(handler, "dispatch", lambda job, ctx: sent.append(job))
    r = handler.handler(event("POST", "/api/chat", body={"question": "Who?", "history": [
        {"q": ["x"], "a": "y"}, {"q": "Q" * 9000, "a": "A" * 9000}]}), None)
    assert r["statusCode"] == 202
    assert sent[0]["history"] == [{"q": "Q" * valves.MAX_QUESTION_CHARS, "a": "A" * 4000}]


def test_portal_loop_bounds_history_itself(monkeypatch):
    class Brt:
        def converse(self, **kw):
            self.messages = kw["messages"]
            return {"output": {"message": {"role": "assistant", "content": [{"text": "ok"}]}}}

    class Idx:
        version, passages, entities, lake = "1.0.0", {}, {}, None

    brt = Brt()
    monkeypatch.setattr(chat, "system_text", lambda idx, private=False: "s")
    chat.ask(Idx(), "now?", [{"q": 5, "a": "x"}, {"q": "Q" * 9000, "a": "A" * 9000}], private=False, brt=brt)
    texts = [m["content"][0]["text"] for m in brt.messages[:2]]
    assert texts == ["Q" * valves.MAX_QUESTION_CHARS, "A" * 4000]


# -- requests -----------------------------------------------------------------------------------

def _post_request(body):
    return handler.handler(event("POST", "/api/requests", private=True, body=body), None)


@pytest.mark.parametrize("version", [{"x": 1}, ["1"], 3, "v" * 33])
def test_request_version_must_be_a_short_string(mixed, version):
    r = _post_request({"question": "Q?", "report": {}, "ontology_version": version})
    assert r["statusCode"] == 400


def test_request_question_is_capped_and_good_requests_are_kept(mixed):
    assert _post_request({"question": "Q" * (valves.MAX_QUESTION_CHARS + 1), "report": {}})["statusCode"] == 400
    assert _post_request({"question": {"x": 1}, "report": {}})["statusCode"] == 400
    assert _post_request({"question": "Q?", "report": {}, "ontology_version": "1.2.0"})["statusCode"] == 201
    assert _post_request({"question": "Q?", "report": {}})["statusCode"] == 201


def test_a_non_json_or_non_object_body_is_a_400(mixed):
    ev = event("POST", "/api/requests", private=True)
    assert handler.handler({**ev, "body": "{nope"}, None)["statusCode"] == 400
    assert handler.handler({**ev, "body": "[1]"}, None)["statusCode"] == 400


# -- errors ---------------------------------------------------------------------------------------

def test_an_unexpected_error_is_generic(mixed, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("mongodb://admin:hunter2@db/ internal detail")
    monkeypatch.setattr(index.Index, "summary_view", boom)
    status, body = _call("/api/summary", private=True)
    assert status == 500 and "hunter2" not in json.dumps(body)


def test_a_failed_question_does_not_leak_internals(mixed, monkeypatch):
    state = State()
    monkeypatch.setattr(handler, "_state", state)
    monkeypatch.setattr(handler, "dispatch", lambda job, ctx: handler.answer_job(job))
    monkeypatch.setenv("AGENT_RUNTIME_ARN", "arn:aws:bedrock-agentcore:eu-west-2:123456789012:runtime/chat-x")

    def boom(*a, **k):
        raise RuntimeError("secret internals at /var/task")
    monkeypatch.setattr(agent_client, "ask", boom)
    r = handler.handler(event("POST", "/api/chat", body={"question": "Who?"}), None)
    item = state.get_chat(json.loads(r["body"])["id"])["body"]
    assert item["status"] == "failed" and "internals" not in item["error"]


def test_a_deliberate_failure_is_told(mixed, monkeypatch):
    state = State()
    monkeypatch.setattr(handler, "_state", state)
    monkeypatch.setattr(index, "load", lambda *a: None)
    handler.answer_job({"id": "j", "sub": "u", "private": False, "question": "Q?", "collection": "m"})
    assert "not built yet" in state.get_chat("j")["body"]["error"]


def test_token_endpoint_body_is_not_in_the_error(monkeypatch):
    monkeypatch.setattr(agent_client, "_clients", {"token_endpoint": "https://t.example/token",
                                                   "public": {"id": "i", "secret": "s"}})
    monkeypatch.setattr(agent_client, "_tokens", {})

    def refuse(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 401, "no", {}, io.BytesIO(b'{"error":"client s3cr3t-id invalid"}'))
    monkeypatch.setattr(agent_client.urllib.request, "urlopen", refuse)
    with pytest.raises(RuntimeError) as e:
        agent_client.service_token(False)
    assert "401" in str(e.value) and "s3cr3t" not in str(e.value)


# -- labels in scope ----------------------------------------------------------------------------

def test_entity_labels_only_name_visible_entities(mixed):
    _, lake = mixed
    idx = index.load(lake, "m")
    e = next(e for e in idx.entities.values() if idx.visible(e, False) and idx.entity_view(e, False)["out"])
    target = idx.entity_view(e, False)["out"][0]["o"]
    idx.entities[target]["scope"] = "private"
    try:
        status, body = _call("/api/entity", private=False, qs={"id": e["id"]})
        assert status == 200 and target not in body["labels"]
        assert target in _call("/api/entity", private=True, qs={"id": e["id"]})[1]["labels"]
        tool = chat.run_tool(idx, "get_entity", {"id": e["id"]}, private=False)
        assert all(r["o_label"] is None for r in tool["out"] if r["o"] == target)
    finally:
        index._cache.clear()


# -- the local server -----------------------------------------------------------------------------

def test_local_server_refuses_other_hosts_and_origins():
    ok = "application/json"
    assert local.refusal("GET", "localhost:8765", None, 8765) is None
    assert local.refusal("GET", "127.0.0.1:8765", "https://evil.example", 8765) is None  # a read is not shared
    assert local.refusal("GET", "evil.example:8765", None, 8765)      # DNS rebinding
    assert local.refusal("GET", "localhost:9999", None, 8765)
    assert local.refusal("GET", None, None, 8765)
    assert local.refusal("POST", "localhost:8765", "http://localhost:8765", 8765, ok) is None
    assert local.refusal("POST", "localhost:8765", None, 8765, ok) is None
    assert local.refusal("POST", "localhost:8765", "https://evil.example", 8765, ok)
    assert local.refusal("POST", "localhost:8765", "null", 8765, ok)
    assert local.refusal("POST", "localhost:8765", "http://localhost:8765", 8765, "text/plain")


def test_local_server_sends_no_cors_header(tmp_path, monkeypatch):
    import http.client
    import socketserver
    import threading
    from http.server import ThreadingHTTPServer

    servers = []

    class Server(ThreadingHTTPServer):
        def __init__(self, addr, h):
            super().__init__(("127.0.0.1", 0), h)
            servers.append(self)

        def serve_forever(self, *a):  # serve() returns; the test runs it in a thread
            return None

    monkeypatch.setattr(local, "ThreadingHTTPServer", Server)
    monkeypatch.setattr(handler, "_lake", None)
    monkeypatch.setattr(handler, "_state", None)
    monkeypatch.setattr(handler, "dispatch", handler.dispatch)
    local.serve(str(tmp_path), str(tmp_path), 0)  # the Host check is against the port serve() was given
    srv = servers[0]
    threading.Thread(target=socketserver.BaseServer.serve_forever, args=(srv,), daemon=True).start()

    def call(method, host, origin=None, ctype=None):
        c = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=5)
        c.putrequest(method, "/api/status", skip_host=True)
        c.putheader("Host", host)
        for k, v in (("Origin", origin), ("Content-Type", ctype)):
            if v:
                c.putheader(k, v)
        c.putheader("Content-Length", "0")
        c.endheaders()
        r = c.getresponse()
        r.read()
        c.close()
        return r.status, {k.lower() for k, _ in r.getheaders()}

    try:
        status, headers = call("GET", "evil.example")
        assert status == 403 and "access-control-allow-origin" not in headers
        status, headers = call("GET", "localhost:0", "https://evil.example")
        assert status != 403 and "access-control-allow-origin" not in headers
        assert call("POST", "localhost:0", "https://evil.example", "application/json")[0] == 403
        assert call("POST", "localhost:0", "http://localhost:0", "text/plain")[0] == 403
        assert call("POST", "localhost:0", "http://localhost:0", "application/json")[0] != 403
    finally:
        srv.shutdown()
        srv.server_close()


# -- the origin header CloudFront adds -------------------------------------------------------

def test_without_the_origin_secret_set_every_request_passes(monkeypatch):
    monkeypatch.delenv("ORIGIN_SECRET", raising=False)
    assert handler.from_cloudfront({"headers": {}})


def test_with_the_origin_secret_set_only_cloudfront_requests_pass(monkeypatch):
    monkeypatch.setenv("ORIGIN_SECRET", "s3cret")
    assert handler.from_cloudfront({"headers": {"x-origin-verify": "s3cret"}})
    assert handler.from_cloudfront({"headers": {"X-Origin-Verify": "s3cret"}})
    assert not handler.from_cloudfront({"headers": {"x-origin-verify": "wrong"}})
    assert not handler.from_cloudfront({"headers": {}})
    assert not handler.from_cloudfront({})
    res = handler.handler({"rawPath": "/api/collections", "requestContext": {"http": {"method": "GET"}}, "headers": {}}, None)
    assert res["statusCode"] == 403


# -- credentials only over https -------------------------------------------------------------

def test_the_service_token_is_never_requested_over_plain_http(monkeypatch):
    monkeypatch.setattr(agent_client, "_clients", {"token_endpoint": "http://example.com/oauth2/token",
                                                   "public": {"id": "a", "secret": "b"}})
    monkeypatch.setattr(agent_client, "_tokens", {})
    with pytest.raises(RuntimeError, match="https"):
        agent_client.service_token(False)


def test_the_eval_runner_sends_its_token_only_over_https_or_to_localhost():
    from knowledge_store.evaluation.adapters.run import api_target
    for bad in ("http://example.com", "ftp://example.com", "file:///etc/passwd"):
        with pytest.raises(SystemExit):
            api_target(bad, "tok", "c")
    api_target("https://example.com", "tok", "c")
    api_target("http://localhost:8765", "tok", "c")
