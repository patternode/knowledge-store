"""The agent client: asking the chat agent on AgentCore Runtime, as the person or a service client.

The network is stubbed at the adapter boundary (urllib.request.urlopen and the secret read).
"""

from __future__ import annotations

import io
import json
import urllib.error

import pytest

from knowledge_store.answering.adapters import agent_client as ac

ARN = "arn:aws:bedrock-agentcore:eu-west-2:123456789012:runtime/agent-abc"


class Response(io.BytesIO):
    def __init__(self, body: bytes, content_type: str = "application/json"):
        super().__init__(body)
        self.headers = {"content-type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def __iter__(self):
        return iter(self.getvalue().splitlines())


@pytest.fixture
def opened(monkeypatch):
    """Every request urlopen is given, and the responses it returns in turn."""
    seen, queue = [], []

    def urlopen(req, timeout=None):
        seen.append(req)
        r = queue.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    monkeypatch.setattr(ac.urllib.request, "urlopen", urlopen)
    return seen, queue


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    ac._clients.clear()
    ac._tokens.clear()
    monkeypatch.setenv("AGENT_RUNTIME_ARN", ARN)
    monkeypatch.delenv("AGENT_RUNTIME_QUALIFIER", raising=False)
    yield
    ac._clients.clear()
    ac._tokens.clear()


def clients(endpoint="https://auth.example.com/oauth2/token"):
    ac._clients.update({"token_endpoint": endpoint, "public": {"id": "pub", "secret": "s1"},
                        "private": {"id": "priv", "secret": "s2"}})


def http_error(code):
    return urllib.error.HTTPError("u", code, "err", {}, io.BytesIO(b"denied"))


def test_the_invocation_url_names_the_region_and_the_escaped_runtime():
    url = ac.invocation_url(ARN, "DEFAULT")
    assert url.startswith("https://bedrock-agentcore.eu-west-2.amazonaws.com/runtimes/arn%3Aaws%3A")
    assert url.endswith("/invocations?qualifier=DEFAULT")


def test_configured_only_with_a_runtime(monkeypatch):
    assert ac.configured()
    monkeypatch.delenv("AGENT_RUNTIME_ARN")
    assert not ac.configured()


def test_a_session_is_per_person_and_scope_and_never_carries_the_subject():
    a, b = ac.session_for("alice", False), ac.session_for("alice", True)
    assert a != b and a == ac.session_for("alice", 0)
    assert "alice" not in a and len(a) >= 33


def test_asking_sends_the_bearer_token_and_a_padded_session(opened):
    seen, queue = opened
    queue.append(Response(json.dumps({"answer": "yes"}).encode()))
    assert ac.ask("tok", {"q": "Q?"}, session_id="short") == {"answer": "yes"}
    req = seen[0]
    assert req.get_header("Authorization") == "Bearer tok"
    assert req.get_header("X-amzn-bedrock-agentcore-runtime-session-id") == "short".ljust(33, "0")
    assert json.loads(req.data) == {"q": "Q?", "stream": False}


def test_an_answer_encoded_twice_is_decoded(opened):
    _, queue = opened
    queue.append(Response(json.dumps(json.dumps({"answer": "yes"})).encode()))
    assert ac.ask("tok", {}) == {"answer": "yes"}


def test_a_streamed_answer_reports_each_step(opened):
    seen, queue = opened
    queue.append(Response(b'data: {"step": {"n": 1}}\n\ndata: {"result": {"answer": "ok"}}\n', "text/event-stream"))
    steps = []
    assert ac.ask("tok", {}, on_step=steps.append) == {"answer": "ok"} and steps == [{"n": 1}]
    assert json.loads(seen[0].data)["stream"] is True
    assert "text/event-stream" in seen[0].get_header("Accept")


def test_an_agent_that_does_not_stream_still_answers_a_streaming_ask(opened):
    _, queue = opened
    queue.append(Response(b'{"answer": "plain"}'))
    assert ac.ask("tok", {}, on_step=lambda s: None) == {"answer": "plain"}


def test_a_refused_invocation_is_an_error_without_the_body(opened):
    _, queue = opened
    queue.append(http_error(403))
    with pytest.raises(RuntimeError, match=r"the agent failed \(403\)"):
        ac.ask("tok", {})


def test_events_that_are_not_json_or_not_objects_are_skipped():
    lines = ["data: not json", "data: [1, 2]", 'data: {"result": {"answer": "a"}}', 'data: {"error": "late"}']
    assert ac.read_events(lines, None) == {"answer": "a"}


def test_a_stream_whose_result_is_not_an_object_is_a_failure():
    assert "error" in ac.read_events(['data: {"result": "text"}'], None)


# --- service clients ---------------------------------------------------------------------------

def test_a_service_token_is_fetched_with_client_credentials(opened):
    seen, queue = opened
    clients()
    queue.append(Response(json.dumps({"access_token": "svc", "expires_in": 3600}).encode()))
    assert ac.service_token(private=True, now=1000) == "svc"
    req = seen[0]
    assert req.data == b"grant_type=client_credentials" and req.get_header("Authorization").startswith("Basic ")
    import base64
    assert base64.b64decode(req.get_header("Authorization")[6:]) == b"priv:s2"


def test_a_service_token_is_reused_until_a_minute_before_it_expires(opened):
    _, queue = opened
    clients()
    queue += [Response(b'{"access_token": "one", "expires_in": 600}'), Response(b'{"access_token": "two", "expires_in": 600}')]
    assert ac.service_token(False, now=0) == "one"
    assert ac.service_token(False, now=500) == "one"
    assert ac.service_token(False, now=545) == "two"


def test_the_public_and_private_tokens_are_kept_apart(opened):
    _, queue = opened
    clients()
    queue += [Response(b'{"access_token": "pub-t"}'), Response(b'{"access_token": "priv-t"}')]
    assert ac.service_token(False, now=0) == "pub-t" and ac.service_token(True, now=0) == "priv-t"


def test_a_token_endpoint_that_is_not_https_is_refused_before_the_secret_is_sent(opened):
    seen, _ = opened
    clients("http://auth.example.com/token")
    with pytest.raises(RuntimeError, match="https"):
        ac.service_token(False, now=0)
    assert seen == []


def test_a_failed_service_sign_in_is_an_error(opened):
    _, queue = opened
    clients()
    queue.append(http_error(401))
    with pytest.raises(RuntimeError, match=r"service sign-in failed \(401\)"):
        ac.service_token(False, now=0)


def test_the_service_clients_are_read_once_from_their_secret(monkeypatch):
    boto3 = pytest.importorskip("boto3")
    reads = []

    class Secrets:
        def get_secret_value(self, SecretId):
            reads.append(SecretId)
            return {"SecretString": json.dumps({"token_endpoint": "https://t", "public": {"id": "a", "secret": "b"}})}

    monkeypatch.setattr(boto3, "client", lambda name, **kw: Secrets())
    monkeypatch.setenv("SERVICE_CLIENTS_SECRET", "ks/service-clients")
    assert ac._service_clients()["token_endpoint"] == "https://t"
    ac._service_clients()
    assert reads == ["ks/service-clients"]
