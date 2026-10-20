"""The portal API Lambda (apps/portal_api.py) end to end over a swept lake, with the chat state in
memory: the routes a reader uses, and its refusals."""

from __future__ import annotations

import json

import pytest

from knowledge_store.apps import portal_api as handler
from test_chat_api import State, event
from test_review_fixes import mixed  # noqa: F401


def call(method, path, private=False, **kw):
    r = handler.handler(event(method, path, private=private, **kw), None)
    return r["statusCode"], json.loads(r["body"])


class UsageState(State):
    def get_usage(self, cid, bucket):
        return {}


@pytest.fixture
def ready(mixed, monkeypatch):
    monkeypatch.setattr(handler, "_state", UsageState())
    monkeypatch.delenv("ORIGIN_SECRET", raising=False)
    monkeypatch.delenv("SITE_GRANT_ISSUER", raising=False)
    monkeypatch.delenv("AGENT_RUNTIME_ARN", raising=False)
    return mixed


def test_a_reader_lists_collections_and_reads_the_graph(ready):
    status, body = call("GET", "/api/collections")
    assert status == 200 and [c["id"] for c in body["collections"]] == ["m"] and body["private"] is False
    assert call("GET", "/api/status")[1]["stage"] == "ready"
    status, summary = call("GET", "/api/summary")
    assert status == 200 and summary["private"] is False
    status, found = call("GET", "/api/entities", qs={"q": "Alpha"})
    assert status == 200 and found["total"] >= 1
    entity = found["entities"][0]["id"] if "entities" in found else found["items"][0]["id"]
    status, view = call("GET", "/api/entity", qs={"id": entity})
    assert status == 200 and "labels" in view
    assert call("GET", "/api/graph")[0] == 200 and call("GET", "/api/ontology")[0] == 200


def test_a_question_is_accepted_and_dispatched(ready, monkeypatch):
    jobs = []
    monkeypatch.setattr(handler, "dispatch", lambda job, ctx: jobs.append(job))
    status, body = call("POST", "/api/chat", body={"question": "Who launched Mission Alpha?"})
    assert status == 202 and jobs[0]["id"] == body["id"] and jobs[0]["collection"] == "m"
    status, item = call("GET", "/api/chat", qs={"id": body["id"]})
    assert status == 200 and item["status"] == "pending"


def test_another_persons_question_is_not_found(ready, monkeypatch):
    monkeypatch.setattr(handler, "dispatch", lambda job, ctx: None)
    _, body = call("POST", "/api/chat", body={"question": "?"})
    other = handler.handler({**event("GET", "/api/chat", qs={"id": body["id"]}),
                             "requestContext": {"http": {"method": "GET"},
                                                "authorizer": {"jwt": {"claims": {"sub": "someone-else"}}}}}, None)
    assert other["statusCode"] == 404


def test_an_unknown_collection_or_route_is_not_found(ready):
    assert call("GET", "/api/status", qs={"c": "nope"})[0] == 404
    assert call("GET", "/api/nowhere")[0] == 404


def test_requests_and_drafts_are_for_curators(ready):
    assert call("GET", "/api/requests")[0] == 403
    assert call("GET", "/api/requests", private=True) == (200, {"requests": []})
    status, body = call("POST", "/api/requests", private=True, body={"question": "Why?", "report": {"gaps": []}})
    assert status == 201 and call("GET", "/api/requests", private=True)[1]["requests"][0]["id"] == body["id"]


def test_a_question_over_the_daily_limit_is_refused(ready, monkeypatch):
    monkeypatch.setattr(handler, "dispatch", lambda job, ctx: None)
    monkeypatch.setattr(handler, "take_quota", lambda sub: False)
    assert call("POST", "/api/chat", body={"question": "?"})[0] == 429


def test_without_the_origin_secret_header_it_is_forbidden(ready, monkeypatch):
    monkeypatch.setenv("ORIGIN_SECRET", "s3cret")
    assert call("GET", "/api/status") == (403, {"error": "Forbidden"})


def test_usage_needs_a_known_window(ready):
    assert call("GET", "/api/usage", qs={"window": "year"})[0] == 400
    status, body = call("GET", "/api/usage")
    assert status == 200 and body["window"] == "all" and body["bucket"] == "all"
