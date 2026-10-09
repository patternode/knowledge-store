"""The workbench: the steps of a question and the ontology terms they touch, the usage totals the
portal keeps from them, ontology requests, and the analyst over the portal's own tool loop."""

from __future__ import annotations

import json

import pytest

from knowledge_store import layout, workbench
from knowledge_store.ontology import candidates, versions
from knowledge_store.portal_api import agent_client, chat, handler, index
from knowledge_store.portal_api.state import MemoryState
from knowledge_store.tools import gateway
from test_review_fixes import mixed  # noqa: F401


def call(root, name, args, private=False):
    return gateway.call(root, name, {"collection": "m", **args, "caller_private": private})


def test_steps_and_terms_from_real_tool_results(mixed):
    root, _ = mixed
    seen = []
    rec = workbench.Recorder(seen.append)
    found = call(root, "search_entities", {"query": "Mission Alpha", "type": "Mission"})
    rec.tool("search_entities", {"collection": "m", "query": "Mission Alpha", "type": "Mission"}, found)
    ent = call(root, "get_entity", {"id": found["items"][0]["id"]})
    rec.tool("kg___get_entity", {"id": ent["id"], "caller_private": True}, ent)
    assert [s["tool"] for s in seen] == ["search_entities", "get_entity"]  # emitted as they happen
    assert seen[0]["title"].startswith("Searched entities for “Mission Alpha” of type Mission")
    assert "caller_private" not in seen[1]["input"]
    hits = rec.hits()
    assert "queried" in hits["classes"]["Mission"] and "read" in hits["classes"]["Mission"]
    rel = next(r for r in ent["out"] if r["passages"])
    assert hits["relations"][rel["p"]] == ["read"]
    rec.cite(rel["passages"][:1])
    assert rec.hits()["relations"][rel["p"]] == ["read", "cited"]


def test_a_failing_tool_is_a_step_and_touches_nothing():
    rec = workbench.Recorder()
    s = rec.tool("get_entity", {"id": "nope"}, {"error": "no entity 'nope'"})
    assert s["title"] == "get_entity failed" and s["error"] and rec.hits() == {}


def test_backfill_reads_a_finished_conversation():
    rec = workbench.Recorder()
    rec.backfill([
        {"role": "assistant", "content": [{"toolUse": {"toolUseId": "t1", "name": "list_entities", "input": {"type": "Agency"}}}]},
        {"role": "user", "content": [{"toolResult": {"toolUseId": "t1", "content": [
            {"text": json.dumps({"items": [{"id": "a", "label": "Agency Nova", "type": "Agency"}]})}]}}]}])
    assert rec.tool_calls == 1 and rec.hits()["classes"]["Agency"] == ["queried", "read"]


def test_usage_counts_and_view_round_trip():
    hits = {"classes": {"Mission": ["queried", "read"]}, "relations": {"launchedBy": ["cited"]}, "bogus": {"x": ["read"]}}
    counts = workbench.usage_counts(hits)
    assert counts == {"classes|Mission|queried": 1, "classes|Mission|read": 1, "relations|launchedBy|cited": 1}
    v = workbench.usage_view({**counts, "questions": 1})
    assert v["questions"] == 1 and v["classes"]["Mission"] == {"queried": 1, "read": 1, "cited": 0}
    assert v["attributes"] == {}


def test_clean_report_keeps_only_the_schema():
    r = workbench.clean_report({"verdict": "nonsense", "summary": "s" * 5000, "extra": 1,
                                "ontology": {"classes": [{"name": "LaunchCost", "definition": "d", "junk": 1}, {"definition": "no name"}]},
                                "rewrites": ["ok", 3, " "]})
    assert r["verdict"] == "data_missing" and len(r["summary"]) == 1500
    assert r["ontology"]["classes"] == [{"name": "LaunchCost", "definition": "d"}] and r["rewrites"] == ["ok"]


# --- the portal: steps while running, usage totals, requests --------------------------------------------

def event(method, path, private=False, body=None, qs=None):
    groups = "[private-readers]" if private else "[]"
    return {"rawPath": path, "headers": {"authorization": "Bearer tok-1"},
            "requestContext": {"http": {"method": method},
                               "authorizer": {"jwt": {"claims": {"sub": "u", "cognito:groups": groups}}}},
            "queryStringParameters": {"c": "m", **(qs or {})}, "body": json.dumps(body) if body else None}


@pytest.fixture
def portal(mixed, monkeypatch):
    root, lake = mixed
    st = MemoryState()
    monkeypatch.setattr(handler, "_state", st)
    monkeypatch.setattr(handler, "_lake", root)
    monkeypatch.setattr(handler, "dispatch", lambda job, ctx: handler.answer_job(job))
    monkeypatch.setenv("AGENT_RUNTIME_ARN", "arn:aws:bedrock-agentcore:eu-west-2:123456789012:runtime/chat-x")
    return root, lake, st


def test_steps_show_while_running_and_usage_is_recorded(portal, monkeypatch):
    _, _, st = portal
    seen_running = []
    seen_session = []

    def ask(token, payload, on_step=None, **kw):
        on_step({"n": 1, "kind": "tool", "title": "Read the ontology"})
        seen_running.append(st.chats[next(iter(st.chats))]["body"])
        seen_session.append(kw.get("session_id"))
        return {"answer": "Agency Nova launched it. [1]", "sources": [{"n": 1}], "steps": [{"n": 1}],
                "ontology_hits": {"classes": {"Mission": ["queried", "read"]}, "relations": {"launchedBy": ["cited"]}}}

    monkeypatch.setattr(agent_client, "ask", ask)
    r = handler.handler(event("POST", "/api/chat", body={"question": "Who launched Mission Alpha?"}), None)
    assert r["statusCode"] == 202
    assert seen_session == [agent_client.session_for("u", False)]
    assert seen_running[0]["status"] == "running" and seen_running[0]["steps"][0]["title"] == "Read the ontology"
    usage = json.loads(handler.handler(event("GET", "/api/usage"), None)["body"])
    assert usage["questions"] == 1 and usage["classes"]["Mission"]["queried"] == 1
    assert usage["relations"]["launchedBy"]["cited"] == 1
    month = json.loads(handler.handler(event("GET", "/api/usage", qs={"window": "month"}), None)["body"])
    assert month["bucket"] == workbench.month() and month["questions"] == 1
    assert handler.handler(event("GET", "/api/usage", qs={"window": "year"}), None)["statusCode"] == 400


def test_a_gaps_question_goes_to_the_analyst_and_is_not_counted(portal, monkeypatch):
    _, _, st = portal
    asked = []
    monkeypatch.setattr(agent_client, "ask", lambda token, payload, **kw: asked.append(payload) or {
        "mode": "gaps", "report": {"verdict": "ontology_missing", "summary": "No cost."},
        "ontology_hits": {"classes": {"Mission": ["read"]}}})
    r = handler.handler(event("POST", "/api/chat", body={
        "question": "What did Mission Alpha cost?", "mode": "gaps",
        "about": {"answer": "I can't answer that.", "gaps": ["the cost"], "steps": ["Searched"], "junk": 1}}), None)
    assert asked[0]["mode"] == "gaps" and asked[0]["about"] == {"answer": "I can't answer that.", "gaps": ["the cost"], "steps": ["Searched"]}
    item = st.get_chat(json.loads(r["body"])["id"])["body"]
    assert item["status"] == "done" and item["report"]["verdict"] == "ontology_missing"
    assert st.get_usage("m", "all") == {}  # only answered questions count
    bad = handler.handler(event("POST", "/api/chat", body={"question": "x", "mode": "other"}), None)
    assert bad["statusCode"] == 400


def test_requests_are_for_curators_and_feed_the_candidate_register(portal):
    root, lake, _ = portal
    report = {"verdict": "ontology_missing", "summary": "No cost is recorded.",
              "ontology": {"attributes": [{"name": "launchCost", "domain": "Mission", "datatype": "decimal",
                                           "definition": "What a launch cost, in US dollars."}]}}
    body = {"question": "What did Mission Alpha cost?", "report": report, "ontology_version": "1.0.0"}
    assert handler.handler(event("POST", "/api/requests", body=body), None)["statusCode"] == 403
    assert handler.handler(event("GET", "/api/requests"), None)["statusCode"] == 403
    assert handler.handler(event("POST", "/api/requests", private=True, body=body), None)["statusCode"] == 201
    assert handler.handler(event("POST", "/api/requests", private=True, body={"question": "x"}), None)["statusCode"] == 400
    got = json.loads(handler.handler(event("GET", "/api/requests", private=True), None)["body"])["requests"]
    assert got[0]["question"] == body["question"] and got[0]["by"] == "u"
    reg = candidates.build_register(lake, versions.active_version(lake))
    row = next(t for t in reg["terms"] if t["term"] == "launchCost")
    assert row["kind"] == "attribute" and row["asked"] == 1 and row["questions"] == [body["question"]]


# --- the portal's own loop: steps, and the analyst --------------------------------------------------------

class Scripted:
    """A Converse client that plays back prepared assistant messages."""

    def __init__(self, *messages):
        self.messages, self.requests = list(messages), []

    def converse(self, **kw):
        self.requests.append(kw)
        return {"output": {"message": {"role": "assistant", "content": self.messages.pop(0)}}, "usage": {}}


def tool_use(name, args, i="t1"):
    return [{"toolUse": {"toolUseId": i, "name": name, "input": args}}]


def test_sample_questions_keep_a_named_level_and_otherwise_spread():
    from knowledge_store.config import profile_from_dict
    named = profile_from_dict({"example_questions": [
        "[low] Where does Moriarty appear?",
        {"text": "Who did he let go, and why?", "level": "high"},
        "Which clients came in disguise?",
    ]})
    assert named.example_questions[0] == "Where does Moriarty appear?"
    assert [q["level"] for q in named.sample_questions()] == ["low", "high", "medium"]
    assert "example_questions" in named.to_dict() and "question_levels" not in named.to_dict()
    plain = profile_from_dict({"example_questions": ["one lookup", "a connection", "a comparison", "another connection"]})
    assert [q["level"] for q in plain.sample_questions()] == ["low", "medium", "medium", "high"]


def test_a_question_is_priced_by_token_kind_and_by_model_call(mixed):
    _, lake = mixed
    idx = index.load(lake, "m-cost")
    usage = [
        {"inputTokens": 1000, "outputTokens": 50, "cacheWriteInputTokens": 0, "cacheReadInputTokens": 0},
        {"inputTokens": 200, "outputTokens": 40, "cacheWriteInputTokens": 0, "cacheReadInputTokens": 800},
    ]

    class Priced:
        def __init__(self):
            self.n = 0

        def converse(self, **kw):
            n, self.n = self.n, self.n + 1
            content = tool_use("search_entities", {"query": "Alpha"}) if n == 0 else [{"text": "Nothing there."}]
            return {"output": {"message": {"role": "assistant", "content": content}}, "usage": usage[n]}

    out = chat.ask(idx, "Who launched Mission Alpha?", None, private=False, brt=Priced(),
                   model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0")
    calls = [s for s in out["steps"] if s["kind"] == "model"]
    assert len(calls) == 2 and calls[0]["usd"] > 0 and calls[1]["usage"]["cacheReadInputTokens"] == 800
    cost = out["cost"]
    assert cost["priced"] and "10%" in cost["note"]
    parts = {p["key"]: p for p in cost["parts"]}
    assert parts["input"]["tokens"] == 1200 and parts["output"]["tokens"] == 90 and parts["cache_read"]["tokens"] == 800
    assert parts["cache_write"]["usd"] == 0
    assert sum(p["usd"] for p in cost["parts"]) == pytest.approx(cost["usd"], abs=1e-4)
    assert sum(c["usd"] for c in cost["calls"]) == pytest.approx(cost["usd"], abs=1e-4)
    # 1,200 input at $3, 90 output at $15, 800 cache read at $0.30, per million, then Bedrock's 10%.
    assert cost["usd"] == pytest.approx((1200 * 3 + 90 * 15 + 800 * 0.30) / 1e6 * 1.1, abs=1e-6)


def test_collections_include_the_sample_questions(portal):
    root, lake, _ = portal
    from knowledge_store.store import put_json
    put_json(lake, layout.CONFIG_PROFILE, {"name": "Missions", "example_questions": [
        "[low] Which missions returned samples?", "[high] Which also flew a gravity assist, and why?"]})
    body = json.loads(handler.handler(event("GET", "/api/collections"), None)["body"])
    samples = body["collections"][0]["example_questions"]
    assert samples == [
        {"text": "Which missions returned samples?", "level": "low"},
        {"text": "Which also flew a gravity assist, and why?", "level": "high"},
    ]


def test_the_portal_loop_reports_steps_and_terms(mixed):
    _, lake = mixed
    idx = index.load(lake, "m-steps")
    steps = []
    brt = Scripted(tool_use("search_entities", {"query": "Mission Alpha", "type": "Mission"}), [{"text": "No idea."}])
    out = chat.ask(idx, "Who launched Mission Alpha?", None, private=False, brt=brt, on_step=steps.append)
    assert [s["kind"] for s in out["steps"]] == ["tool", "model", "tool", "model", "done"] and steps == out["steps"]
    assert "queried" in out["ontology_hits"]["classes"]["Mission"]


def test_the_analyst_explores_then_reports(mixed):
    _, lake = mixed
    idx = index.load(lake, "m-analyst")
    brt = Scripted(tool_use("search_entities", {"query": "cost"}),
                   tool_use("submit_report", {"verdict": "ontology_missing", "summary": "No cost attribute.",
                                              "ontology": {"attributes": [{"name": "launchCost", "domain": "Mission",
                                                                           "definition": "d"}]}}, "t2"))
    out = chat.analyse(idx, "What did Mission Alpha cost?", {"gaps": ["the cost"]}, private=False, brt=brt)
    assert out["mode"] == "gaps" and out["report"]["ontology"]["attributes"][0]["name"] == "launchCost"
    assert "the cost" in brt.requests[0]["messages"][0]["content"][0]["text"]
    assert any(t["toolSpec"]["name"] == "submit_report" for t in brt.requests[0]["toolConfig"]["tools"])
    assert "toolChoice" not in brt.requests[0]["toolConfig"]


def test_streamed_events_are_read_in_order():
    steps = []
    lines = [b"data: " + json.dumps({"step": {"n": 1}}).encode(), b"", b": keep-alive",
             b"data: " + json.dumps({"step": {"n": 2}}).encode(),
             b"data: " + json.dumps(json.dumps({"result": {"answer": "yes"}})).encode()]
    assert agent_client.read_events(lines, steps.append) == {"answer": "yes"} and steps == [{"n": 1}, {"n": 2}]
    assert "error" in agent_client.read_events([b'data: {"error": "boom"}'], steps.append)
    assert "error" in agent_client.read_events([], steps.append)
