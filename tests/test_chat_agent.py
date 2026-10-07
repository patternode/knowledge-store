"""The chat agent's grounding and valves, with a scripted agent in place of the model: what the
model claims is checked against the passages the caller can read, and only checked claims are shown."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from knowledge_store.agent import app, grounding, valves
from knowledge_store.agent.grounding import Citation, Claim, GroundedAnswer
from knowledge_store.tools import gateway
from test_review_fixes import mixed  # noqa: F401


class Tools:
    """The Gateway's tools in-process, in one scope, without the agent framework."""

    def __init__(self, root, private=False):
        self.root, self.private, self.tools, self.calls = root, private, [], []

    def call(self, name, args):
        self.calls.append(name)
        return gateway.call(self.root, name, {**args, "caller_private": self.private})


class Scripted:
    """An agent that returns prepared answers, one per call."""

    def __init__(self, *answers):
        self.answers, self.prompts, self.messages = list(answers), [], []

    def __call__(self, prompt):
        self.prompts.append(prompt)
        return SimpleNamespace(structured_output=self.answers.pop(0))


def passage_with(root, text, private=True):
    hits = gateway.call(root, "search_passages", {"collection": "m", "query": text, "caller_private": private})
    return next(p for p in hits["passages"] if text.lower() in p["text"].lower())


def ask(root, *answers, private=False, guardrail=None, question="Who launched Mission Alpha?"):
    agent = Scripted(*answers)
    out = app.answer(question, "m", None, Tools(root, private), guardrail=guardrail, agent_factory=lambda: agent)
    return out, agent


def claim(text, pid, quote):
    return Claim(text=text, citations=[Citation(passage_id=pid, quote=quote)])


# --- the checks themselves ------------------------------------------------------------------------

def test_quotes_match_through_case_spacing_quotes_and_dashes():
    text = "Mission Alpha was launched by\nAgency Nova in 2011 — the “first”."
    assert grounding.quote_in("mission alpha was launched by agency nova", text)
    assert grounding.quote_in('in 2011 - the "first"', text)
    assert not grounding.quote_in("launched by Agency Orbis", text)
    assert not grounding.quote_in("Alpha", text)  # too short to say anything


def test_render_numbers_sources_in_order_of_first_citation():
    ps = {"p1": {"doc": "d1", "title": "A", "text": "x"}, "p2": {"doc": "d2", "title": "B", "text": "y"}}
    out = grounding.render([claim("One.", "p2", "q"), Claim(text="Two.", citations=[
        Citation(passage_id="p1", quote="r"), Citation(passage_id="p2", quote="s")])], ps, [])
    assert out["answer"] == "One. [1] Two. [2][1]"
    assert [s["passage_id"] for s in out["sources"]] == ["p2", "p1"] and out["sources"][0]["quotes"] == ["q", "s"]


# --- the agent's answers --------------------------------------------------------------------------

def test_a_grounded_answer_is_shown_with_its_sources(mixed):
    root, _ = mixed
    p = passage_with(root, "Mission Alpha was launched by Agency Nova", private=False)
    out, _ = ask(root, GroundedAnswer(answerable=True, claims=[
        claim("Agency Nova launched Mission Alpha, in 2011.", p["id"], "Mission Alpha was launched by Agency Nova in 2011")]))
    assert not out["abstained"] and out["answer"].endswith("[1]")
    assert out["sources"][0]["passage_id"] == p["id"] and "Agency Nova" in out["sources"][0]["text"]
    assert out["grounding"]["claims_shown"] == 1 and out["ontology_version"]


def test_an_invented_quote_is_removed_and_nothing_unchecked_is_shown(mixed):
    root, _ = mixed
    p = passage_with(root, "Mission Alpha was launched by Agency Nova", private=False)
    good = claim("Agency Nova launched Mission Alpha.", p["id"], "Mission Alpha was launched by Agency Nova")
    bad = claim("Mission Alpha cost two billion.", p["id"], "Mission Alpha cost two billion dollars")
    out, agent = ask(root, GroundedAnswer(answerable=True, claims=[good, bad]),
                     GroundedAnswer(answerable=True, claims=[good, bad]))
    assert len(agent.prompts) == 2 and "quote not found" in agent.prompts[1]      # one repair turn
    assert "two billion" not in out["answer"] and out["grounding"]["claims_shown"] == 1


def test_a_repair_that_fixes_the_quote_is_taken(mixed):
    root, _ = mixed
    p = passage_with(root, "Mission Alpha was launched by Agency Nova", private=False)
    wrong = claim("Agency Nova launched Mission Alpha.", p["id"], "Agency Nova launched Mission Alpha")
    right = claim("Agency Nova launched Mission Alpha.", p["id"], "Mission Alpha was launched by Agency Nova")
    out, _ = ask(root, GroundedAnswer(answerable=True, claims=[wrong]), GroundedAnswer(answerable=True, claims=[right]))
    assert not out["abstained"] and out["grounding"]["repairs"] == 1


def test_a_private_passage_cannot_ground_a_public_answer(mixed):
    root, _ = mixed
    p = passage_with(root, "Mission Zeta was launched by Agency Nova", private=True)
    answer = GroundedAnswer(answerable=True, claims=[
        claim("Agency Nova launched Mission Zeta.", p["id"], "Mission Zeta was launched by Agency Nova")])
    public, _ = ask(root, answer, answer, private=False)
    private, _ = ask(root, answer, private=True)
    assert public["abstained"] and "Zeta" not in public["answer"]
    assert not private["abstained"]


def test_unanswerable_abstains_with_gaps(mixed):
    root, _ = mixed
    out, _ = ask(root, GroundedAnswer(answerable=False, claims=[], gaps=["no document gives budgets"]))
    assert out["abstained"] and out["answer"] == grounding.ABSTAIN and out["gaps"] == ["no document gives budgets"]


def test_claims_with_answerable_false_are_not_shown(mixed):
    root, _ = mixed
    p = passage_with(root, "Mission Alpha was launched by Agency Nova", private=False)
    out, _ = ask(root, GroundedAnswer(answerable=False, claims=[
        claim("Agency Nova launched Mission Alpha.", p["id"], "Mission Alpha was launched by Agency Nova")]))
    assert out["abstained"]


class FakeGuardrail:
    def __init__(self, block_question=False, ungrounded=()):
        self.block_question, self.ungrounded = block_question, ungrounded

    def question(self, text):
        return "Blocked." if self.block_question else None

    def grounded(self, question, claim_text, sources):
        return (claim_text not in self.ungrounded, 0.1 if claim_text in self.ungrounded else 0.9)


def test_guardrail_blocks_a_question_before_any_model_call(mixed):
    root, _ = mixed
    out, agent = ask(root, guardrail=FakeGuardrail(block_question=True))
    assert out["answer"] == "Blocked." and out["blocked"] and agent.prompts == []


def test_guardrail_drops_a_claim_its_quote_does_not_support(mixed):
    root, _ = mixed
    p = passage_with(root, "Mission Alpha was launched by Agency Nova", private=False)
    stretch = "Agency Nova is the only agency that launches missions."
    out, _ = ask(root, GroundedAnswer(answerable=True, claims=[
        claim("Agency Nova launched Mission Alpha.", p["id"], "Mission Alpha was launched by Agency Nova"),
        claim(stretch, p["id"], "Mission Alpha was launched by Agency Nova")]), guardrail=FakeGuardrail(ungrounded=[stretch]))
    assert stretch not in out["answer"] and out["grounding"]["guardrail_dropped"][0]["text"] == stretch


def test_a_failing_agent_claims_nothing(mixed):
    root, _ = mixed

    class Broken:
        messages = []

        def __call__(self, prompt):
            raise RuntimeError("model call budget spent")
    out = app.answer("Who launched Mission Alpha?", "m", None, Tools(root), agent_factory=Broken)
    assert out["abstained"] and "budget" in out["error"]


def test_question_limits():
    assert "error" in app.answer("", "m", None, None)
    assert "error" in app.answer("x" * (valves.MAX_QUESTION_CHARS + 1), "m", None, None)
    assert len(app.history_messages([{"q": "a", "a": "b"}] * 20)) == 2 * valves.MAX_HISTORY_TURNS


def test_tool_and_model_budgets():
    counts, before_tool, before_model = app.limit_hooks()
    tool_ev, model_ev = SimpleNamespace(cancel_tool=False), SimpleNamespace(cancel=False)
    for _ in range(valves.MAX_TOOL_CALLS):
        before_tool(tool_ev)
    assert tool_ev.cancel_tool is False
    before_tool(tool_ev)
    for _ in range(valves.MAX_MODEL_CALLS + 1):
        before_model(model_ev)
    assert tool_ev.cancel_tool == valves.TOOL_BUDGET_SPENT and counts["tools_refused"] == 1
    assert model_ev.cancel and counts["model_calls"] == valves.MAX_MODEL_CALLS + 1


def test_limits_attach_to_a_strands_agent():
    strands = pytest.importorskip("strands")
    assert app.add_limits(strands.Agent(callback_handler=None)) == {"tool_calls": 0, "model_calls": 0, "tools_refused": 0}


def test_local_tools_expose_every_gateway_tool(mixed):
    pytest.importorskip("strands")
    root, _ = mixed
    t = app.LocalTools(root, private=False)
    assert sorted(x.tool_name for x in t.tools) == sorted(gateway.TOOLS)
    assert t.call("describe_ontology", {"collection": "m"})["version"]
