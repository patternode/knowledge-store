"""The portal's own question loop (answering.adapters.fallback_chat), with the model played back.

Runs over the shared `mixed` collection (tests/apps/test_review_fixes.py); the model is a Converse
stub injected through `brt`, and the Anthropic transport is stubbed at urllib.
"""

from __future__ import annotations

import copy
import io
import json

import pytest

from knowledge_store.answering.adapters import fallback_chat as chat
from knowledge_store.knowledge_graph.adapters import index
from test_review_fixes import mixed  # noqa: F401


class Scripted:
    def __init__(self, *messages, usage=None):
        self.messages, self.requests, self.usage = list(messages), [], usage or {}

    def converse(self, **kw):
        self.requests.append(copy.deepcopy(kw))  # the loop keeps appending to the same message list
        content = self.messages.pop(0) if self.messages else [{"text": "Done."}]
        return {"output": {"message": {"role": "assistant", "content": content}}, "usage": self.usage}


def tool_use(name, args, i="t1"):
    return [{"toolUse": {"toolUseId": i, "name": name, "input": args}}]


@pytest.fixture
def idx(mixed):  # noqa: F811
    _, lake = mixed
    return index.load(lake, "m-fallback")


def a_passage(idx, private=False):
    return next(pid for pid, p in idx.passages.items() if idx.visible(p, private))


def test_an_answer_cites_the_passages_it_names(idx):
    pid = a_passage(idx)
    out = chat.ask(idx, "Who launched Mission Alpha?", None, private=False, brt=Scripted([{"text": f"Nova did [p:{pid}]."}]))
    assert [c["id"] for c in out["citations"]] == [pid]
    assert out["steps"][-1]["title"] == "Answered, citing 1 passage"
    assert out["cost"] is None  # the stub reported no usage, which is not zero


def test_a_private_passage_is_not_cited_to_a_public_caller(idx):
    private = next(pid for pid, p in idx.passages.items() if p.get("scope") == "private")
    out = chat.ask(idx, "Q?", None, private=False, brt=Scripted([{"text": f"Secret [p:{private}] [p:nope]."}]))
    assert out["citations"] == []


def test_a_metric_marker_is_shown_only_when_a_tool_returned_that_figure(idx):
    figure = {"id": "m:x", "figure": 3, "metric": "launches"}
    cites = chat.cited(idx, "Three [m:x] and [m:made-up].", False, {"m:x": figure})
    assert [c["id"] for c in cites] == ["m:x"] and cites[0]["kind"] == "metric" and cites[0]["quotes"] == ["3"]


def test_a_cell_marker_that_names_no_readable_cell_is_dropped(idx):
    assert chat.cited(idx, "It cost [c:c:missing].", False) == []


def test_a_repeated_marker_is_cited_once(idx):
    pid = a_passage(idx)
    assert len(chat.cited(idx, f"[p:{pid}] and again [p:{pid}]", False)) == 1


def test_history_is_bounded_and_malformed_turns_are_dropped(idx, monkeypatch):
    monkeypatch.setattr(chat.valves, "MAX_HISTORY_TURNS", 2)
    brt = Scripted([{"text": "ok"}])
    history = [{"q": "one", "a": "1"}, {"q": "", "a": "x"}, {"q": "three", "a": "3"}, "junk"]
    chat.ask(idx, "now?", history, private=False, brt=brt)
    texts = [m["content"][0]["text"] for m in brt.requests[0]["messages"]]
    assert texts == ["three", "3", "now?"]


def test_a_loop_that_never_answers_stops_at_its_step_limit(idx, monkeypatch):
    monkeypatch.setattr(chat, "MAX_STEPS", 2)
    brt = Scripted(tool_use("search_entities", {"query": "a"}), tool_use("search_entities", {"query": "b"}))
    out = chat.ask(idx, "Q?", None, private=False, brt=brt)
    assert out["answer"].startswith("I ran out of steps") and out["steps"][-1]["kind"] == "error"
    assert [t["tool"] for t in out["trace"]] == ["search_entities", "search_entities"]


def test_figures_an_aggregate_returns_can_be_cited(idx, monkeypatch):
    monkeypatch.setattr(chat, "run_tool", lambda i, name, args, private: {"id": "m:n", "figure": 2, "op": "count", "type": "Mission"})
    out = chat.ask(idx, "How many?", None, private=False, brt=Scripted(tool_use("aggregate", {"type": "Mission"}), [{"text": "Two [m:n]."}]))
    assert [c["id"] for c in out["citations"]] == ["m:n"]


def test_the_analyst_is_reminded_to_report_when_it_only_talks(idx):
    brt = Scripted([{"text": "Thinking aloud."}], tool_use("submit_report", {"verdict": "out_of_scope", "summary": "Not here."}))
    out = chat.analyse(idx, "Q?", None, private=False, brt=brt)
    assert out["report"]["verdict"] == "out_of_scope"
    assert brt.requests[1]["messages"][-1]["content"][0]["text"] == "Submit the report with submit_report."


def test_an_analyst_that_never_reports_returns_an_error(idx, monkeypatch):
    monkeypatch.setattr(chat, "MAX_STEPS", 1)
    brt = Scripted(*[tool_use("search_entities", {"query": "x"})] * 3)
    out = chat.analyse(idx, "Q?", None, private=False, brt=brt)
    assert out["error"].startswith("The analyst did not submit a report")
    assert any(b.get("text", "").startswith("Stop exploring now") for b in brt.requests[-1]["messages"][-1]["content"])


@pytest.mark.parametrize("value, provider", [("anthropic", "anthropic"), (" Anthropic ", "anthropic"), ("bedrock", "bedrock"), ("", "bedrock")])
def test_spend_is_priced_as_the_provider_the_portal_calls(monkeypatch, value, provider):
    monkeypatch.setenv("LLM_PROVIDER", value)
    assert chat.spend_provider() == provider


def test_the_anthropic_provider_gets_the_messages_transport(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    assert isinstance(chat.client(), chat._Anthropic)


def test_the_anthropic_transport_speaks_converse(monkeypatch):
    sent = []

    class Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def urlopen(req, timeout=None):
        sent.append(req)
        return Resp(json.dumps({"content": [{"type": "text", "text": "Hi"},
                                            {"type": "tool_use", "id": "tu1", "name": "get_entity", "input": {"id": "e"}}],
                                "stop_reason": "tool_use", "usage": {"input_tokens": 5, "output_tokens": 2}}).encode())

    monkeypatch.setattr(chat.urllib.request, "urlopen", urlopen)
    out = chat._Anthropic("key").converse(modelId="claude-sonnet-4-5", system=[{"text": "s"}],
                                          messages=[{"role": "user", "content": [{"text": "q"}]}],
                                          inferenceConfig={"maxTokens": 10})
    assert sent[0].get_header("X-api-key") == "key"
    assert out["stopReason"] == "tool_use" and out["usage"] == {"inputTokens": 5, "outputTokens": 2}
    assert out["output"]["message"]["content"] == [{"text": "Hi"},
                                                   {"toolUse": {"toolUseId": "tu1", "name": "get_entity", "input": {"id": "e"}}}]
