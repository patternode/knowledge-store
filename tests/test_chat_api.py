"""The chat API with the agent behind it: the question goes to the agent with the person's own
token, the token is never stored, and source documents open only in the person's scope."""

from __future__ import annotations

import json

from knowledge_store.portal_api import agent_client, handler
from test_review_fixes import mixed  # noqa: F401


class State:
    def __init__(self):
        self.items, self.quota = {}, 0

    def take_quota(self, sub, day, limit):
        self.quota += 1
        return self.quota <= limit

    def put_chat(self, cid, sub, body):
        self.items[cid] = {"sub": sub, "body": body}

    def get_chat(self, cid):
        return self.items.get(cid)


def event(method, path, private=False, body=None, qs=None, token="tok-123"):
    groups = "[private-readers]" if private else "[]"
    return {"rawPath": path, "headers": {"Authorization": f"Bearer {token}"},
            "requestContext": {"http": {"method": method},
                               "authorizer": {"jwt": {"claims": {"sub": "u", "cognito:groups": groups}}}},
            "queryStringParameters": {"c": "m", **(qs or {})}, "body": json.dumps(body) if body else None}


def test_questions_go_to_the_agent_as_the_person(mixed, monkeypatch):
    state, sent, asked = State(), [], []
    monkeypatch.setattr(handler, "_state", state)
    monkeypatch.setattr(handler, "dispatch", lambda job, ctx: sent.append(dict(job)) or handler.answer_job(job))
    monkeypatch.setenv("AGENT_RUNTIME_ARN", "arn:aws:bedrock-agentcore:eu-west-2:123456789012:runtime/chat-x")
    monkeypatch.setattr(agent_client, "ask", lambda token, payload, **kw: asked.append((token, payload)) or
                        {"answer": "Agency Nova launched it. [1]", "abstained": False, "sources": [{"n": 1}]})
    r = handler.handler(event("POST", "/api/chat", body={"question": "Who launched Mission Alpha?"}), None)
    assert r["statusCode"] == 202
    cid = json.loads(r["body"])["id"]
    assert asked == [("tok-123", {"question": "Who launched Mission Alpha?", "collection": "m", "history": []})]
    assert "tok-123" not in json.dumps(state.items)          # the token is passed on, never stored
    got = handler.handler(event("GET", "/api/chat", qs={"id": cid}), None)
    assert json.loads(got["body"])["answer"].startswith("Agency Nova")


def test_an_agent_error_is_a_failed_question(mixed, monkeypatch):
    state = State()
    monkeypatch.setattr(handler, "_state", state)
    monkeypatch.setattr(handler, "dispatch", lambda job, ctx: handler.answer_job(job))
    monkeypatch.setenv("AGENT_RUNTIME_ARN", "arn:aws:bedrock-agentcore:eu-west-2:123456789012:runtime/chat-x")
    monkeypatch.setattr(agent_client, "ask", lambda *a, **k: {"error": "no caller token"})
    r = handler.handler(event("POST", "/api/chat", body={"question": "Who?"}), None)
    item = state.get_chat(json.loads(r["body"])["id"])["body"]
    assert item["status"] == "failed" and "no caller token" in item["error"]


def test_documents_open_only_in_scope(mixed):
    root, lake = mixed
    from knowledge_store.pipeline.refine import load_doc, silver_doc_ids
    docs = {load_doc(lake, d)["scope"]: d for d in silver_doc_ids(lake)}
    ok = handler.handler(event("GET", "/api/document", qs={"doc": docs["public"]}), None)
    assert ok["statusCode"] == 200 and json.loads(ok["body"])["doc"] == docs["public"]
    assert handler.handler(event("GET", "/api/document", qs={"doc": docs["private"]}), None)["statusCode"] == 404
    assert handler.handler(event("GET", "/api/document", private=True, qs={"doc": docs["private"]}), None)["statusCode"] == 200
    assert handler.handler(event("GET", "/api/document", qs={"doc": "../x"}), None)["statusCode"] == 404


def test_invocation_url():
    url = agent_client.invocation_url("arn:aws:bedrock-agentcore:eu-west-2:123456789012:runtime/chat-x", "prod")
    assert url == ("https://bedrock-agentcore.eu-west-2.amazonaws.com/runtimes/"
                   "arn%3Aaws%3Abedrock-agentcore%3Aeu-west-2%3A123456789012%3Aruntime%2Fchat-x/invocations?qualifier=prod")
