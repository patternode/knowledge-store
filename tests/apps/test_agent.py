"""The chat agent's deployable (apps/agent.py): it answers only as its caller, within the caller's
daily limit, through the Gateway's tools. The tools, the agent loop and the quota are fakes."""

from __future__ import annotations

import pytest

pytest.importorskip("bedrock_agentcore")

from knowledge_store.apps import agent as app  # noqa: E402


class Tools:
    opened = []

    def __init__(self, url, token):
        Tools.opened.append((url, token))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class Quota:
    def __init__(self, answer=None, error=None):
        self.answer, self.error, self.seen = answer, error, []

    def check(self, token):
        self.seen.append(token)
        if self.error:
            raise self.error
        return self.answer


class Ctx:
    def __init__(self, auth):
        self.request_headers = {"Authorization": auth} if auth else {}


@pytest.fixture
def invoke(monkeypatch):
    Tools.opened = []
    asked = []
    monkeypatch.setattr(app, "GatewayTools", Tools)
    monkeypatch.setattr(app, "run", lambda payload, tools, **kw: asked.append((payload, kw)) or {"answer": "Agency Nova."})
    monkeypatch.setattr(app.Guardrail, "from_env", classmethod(lambda cls: None))
    monkeypatch.setenv("GATEWAY_MCP_URL", "https://gateway.example/mcp")
    monkeypatch.delenv("DEV_BEARER_TOKEN", raising=False)

    def make(quota=None):
        return app.make_app(quota=quota if quota is not None else Quota()).handlers["main"], asked
    return make


def test_a_question_is_answered_as_its_caller(invoke):
    handler, asked = invoke()
    assert handler({"question": "Who launched it?"}, Ctx("Bearer tok-1")) == {"answer": "Agency Nova."}
    assert Tools.opened == [("https://gateway.example/mcp", "tok-1")] and asked[0][0] == {"question": "Who launched it?"}


def test_without_a_caller_token_nothing_is_asked(invoke):
    handler, asked = invoke()
    assert handler({"question": "?"}, Ctx(None)) == {"error": "no caller token: the agent acts only as its caller"}
    assert asked == [] and Tools.opened == []


def test_a_caller_over_the_daily_limit_is_refused(invoke):
    handler, asked = invoke(Quota(answer="You have reached today's question limit."))
    assert handler({"question": "?"}, Ctx("Bearer t")) == {"error": "You have reached today's question limit.", "quota": True}
    assert asked == []


def test_a_limit_that_cannot_be_checked_refuses(invoke):
    handler, asked = invoke(Quota(error=RuntimeError("table down")))
    out = handler({"question": "?"}, Ctx("Bearer t"))
    assert out["quota"] and "could not be checked" in out["error"] and asked == []


def test_a_failure_is_reported_without_its_detail(invoke, monkeypatch):
    handler, _ = invoke()
    monkeypatch.setattr(app, "run", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("secret detail")))
    assert handler({"question": "?"}, Ctx("Bearer t")) == {"error": app.FAILED}


def test_a_streamed_question_returns_the_stream(invoke, monkeypatch):
    handler, _ = invoke()
    monkeypatch.setattr(app, "streamed", lambda work: ("stream", work))
    out = handler({"question": "?", "stream": True}, Ctx("Bearer t"))
    assert out[0] == "stream" and callable(out[1])


def test_the_bearer_prefix_is_optional_and_the_header_case_free():
    class C:
        request_headers = {"authorization": "raw-token"}
    assert app._bearer(C()) == "raw-token"


def test_a_development_token_stands_in_only_without_a_header(monkeypatch):
    monkeypatch.setenv("DEV_BEARER_TOKEN", "dev")
    assert app._bearer(None) == "dev"
    assert app._bearer(Ctx("Bearer real")) == "real"


def test_without_a_quota_every_caller_is_admitted():
    assert app.admit("t", None) is None
