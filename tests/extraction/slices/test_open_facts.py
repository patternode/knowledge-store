"""open_facts: every silver document's facts are recorded once as triples naming their passage,
cleaned of what the model got wrong, and a failure is reported and redone next run."""
from __future__ import annotations

import json

import pytest

from knowledge_store.extraction.slices import open_facts
from knowledge_store.extraction import open_fact_rows
from knowledge_store.ingestion.slices.ingest import ingest
from knowledge_store.ingestion.slices.refine import load_doc, load_passages, refine_all, silver_doc_ids
from knowledge_store.platform_services import SourceConfig, layout
from knowledge_store.platform_services.adapters.store import LocalStore
from test_ingest import FakeSource

DOCS = {
    "alpha.md": "# Alpha\n\nMission Alpha was launched by Agency Nova in 2011.\n\nMission Alpha studies Planet Kiro.",
    "beta.md": "# Beta\n\nMission Beta was launched by Agency Orbis in 2014.\n\nMission Beta carries Instrument Lux.",
}


class TripleClient:
    """Answers record_facts with one triple a sentence, plus one bad passage id and one duplicate."""

    def __init__(self):
        self.calls = []

    def converse(self, **kw):
        self.calls.append(kw)
        text = kw["messages"][0]["content"][0]["text"]
        facts = []
        pid = None
        for line in text.splitlines():
            if line.startswith('<passage id="'):
                pid = line.split('"')[1]
            elif pid and " was launched by " in line:
                subject, rest = line.split(" was launched by ")
                facts.append({"subject": subject, "predicate": "launched by", "object": rest.split(" in ")[0], "passage": pid})
                facts.append({"subject": subject, "predicate": "launched by", "object": rest.split(" in ")[0], "passage": pid})
                facts.append({"subject": subject, "predicate": "launched in", "object": rest.split(" in ")[1].rstrip("."), "passage": pid})
            elif pid and (" studies " in line or " carries " in line):
                verb = "studies" if " studies " in line else "carries"
                subject, obj = line.rstrip(".").split(f" {verb} ")
                facts.append({"subject": subject, "predicate": verb, "object": obj, "passage": pid})
                facts.append({"subject": "Nobody", "predicate": "knows", "object": "Nothing", "passage": pid})
        facts.append({"subject": "Ghost", "predicate": "haunts", "object": "nowhere", "passage": "no-such-passage"})
        facts.append("not a fact")
        return {"output": {"message": {"content": [{"toolUse": {"name": "record_facts", "input": {"facts": facts}}}]}},
                "stopReason": "tool_use", "usage": {"inputTokens": 100, "outputTokens": 20}}


class Failing:
    def converse(self, **kw):
        raise PermissionError("no model access")


class Throttled(TripleClient):
    def __init__(self):
        super().__init__()
        self.left = 2

    def converse(self, **kw):
        if self.left:
            self.left -= 1
            raise RuntimeError("ThrottlingException: slow down")
        return super().converse(**kw)


@pytest.fixture
def lake(tmp_path):
    lake = LocalStore(tmp_path / "lake")
    ingest(lake, SourceConfig("docs", "fake"), FakeSource({k: ("1", v.encode()) for k, v in DOCS.items()}))
    refine_all(lake)
    return lake


def test_every_document_gets_its_facts_once(lake):
    client = TripleClient()
    out = open_facts.extract_open_facts(lake, client, "fake", workers=2)
    assert out["documents"] == out["extracted"] == 2 and out["failed"] == 0 and len(client.calls) == 2
    assert out["usage"]["inputTokens"] == 200
    for doc_id in silver_doc_ids(lake):
        held = json.loads(lake.get(open_facts.facts_key(doc_id)))
        pids = {p.passage_id for p in load_passages(lake, doc_id)}
        assert held["doc_id"] == doc_id and held["model"] == "fake" and all(f["pid"] in pids for f in held["facts"])
        assert held["dropped"] == 2   # the unknown passage id and the non-fact
    again = open_facts.extract_open_facts(lake, client, "fake")
    assert again["documents"] == 0 and len(client.calls) == 2
    redo = open_facts.extract_open_facts(lake, client, "fake", redo=True, limit=1)
    assert redo["documents"] == 1 and len(client.calls) == 3


def test_facts_are_cleaned_deduplicated_and_marked_grounded(lake):
    open_facts.extract_open_facts(lake, TripleClient(), "fake")
    rows = open_fact_rows(lake)
    alpha = [r for r in rows if r["s"] == "Mission Alpha"]
    assert {(r["p"], r["o"]) for r in alpha} == {("launched by", "Agency Nova"), ("launched in", "2011"), ("studies", "Planet Kiro")}
    assert all(r["grounded"] for r in alpha) and all(r["doc"] for r in rows)
    ghost = [r for r in rows if r["s"] == "Nobody"]
    assert ghost and not any(r["grounded"] for r in ghost)   # recorded, but its words are not in the passage


def test_the_model_sees_the_document_and_its_passages_by_id(lake):
    client = TripleClient()
    doc_id = silver_doc_ids(lake)[0]
    open_facts.extract_doc(lake, client, "fake", doc_id)
    text = client.calls[0]["messages"][0]["content"][0]["text"]
    assert text.startswith(f"Document: {load_doc(lake, doc_id)['title']}.")
    assert all(f'<passage id="{p.passage_id}">' in text for p in load_passages(lake, doc_id))
    assert client.calls[0]["toolConfig"]["toolChoice"] == {"tool": {"name": "record_facts"}}


def test_a_failed_document_is_reported_and_redone_next_run(lake):
    out = open_facts.extract_open_facts(lake, Failing(), "fake")
    assert out["failed"] == 2 and all("no model access" in r["error"] for r in out["rows"])
    assert not list(lake.list(layout.SILVER_FACTS + "/"))
    assert open_facts.extract_open_facts(lake, TripleClient(), "fake")["extracted"] == 2


def test_a_throttled_call_is_retried(lake, monkeypatch):
    monkeypatch.setattr(open_facts.time, "sleep", lambda s: None)
    out = open_facts.extract_open_facts(lake, Throttled(), "fake", limit=1)
    assert out["extracted"] == 1


def test_a_model_throttled_every_time_gives_up(lake, monkeypatch):
    monkeypatch.setattr(open_facts.time, "sleep", lambda s: None)
    monkeypatch.setattr(open_facts, "THROTTLE_ATTEMPTS", 2)

    class Always:
        def converse(self, **kw):
            raise RuntimeError("ThrottlingException")
    out = open_facts.extract_open_facts(lake, Always(), "fake", limit=1)
    assert out["failed"] == 1 and "throttled 2 times" in out["rows"][0]["error"]


def test_a_model_that_does_not_call_the_tool_fails_that_document(lake):
    class Talker:
        def converse(self, **kw):
            return {"output": {"message": {"content": [{"text": "here are some facts"}]}}, "stopReason": "end_turn"}
    out = open_facts.extract_open_facts(lake, Talker(), "fake", limit=1)
    assert out["failed"] == 1 and "record_facts" in out["rows"][0]["error"]


def test_clean_facts_keeps_at_most_the_cap_and_only_well_formed_rows():
    from knowledge_store.ingestion import Passage
    p = Passage("pid-1", "d", 0, 0, 10, "h", "A likes B.")
    raw = [{"subject": "A", "predicate": "likes", "object": "B", "passage": "pid-1"}] * 3
    raw += [{"subject": "", "predicate": "x", "object": "y", "passage": "pid-1"}, {"subject": "A", "predicate": "x", "object": "y"}]
    facts, dropped = open_facts.clean_facts(raw, [p])
    assert [f["s"] for f in facts] == ["A"] and dropped == 2 and facts[0]["grounded"]
    assert open_facts.clean_facts("nonsense", [p]) == ([], 0)
    many = [{"subject": f"s{i}", "predicate": "p", "object": "o", "passage": "pid-1"} for i in range(open_facts.MAX_FACTS + 5)]
    assert len(open_facts.clean_facts(many, [p])[0]) == open_facts.MAX_FACTS


def test_a_long_document_is_sent_in_batches_of_passages(lake, monkeypatch):
    from knowledge_store.ingestion import Passage
    doc_id = silver_doc_ids(lake)[0]
    one = load_passages(lake, doc_id)[0]
    three = [Passage(f"{one.passage_id}-{i}", doc_id, i, 0, len(one.text), one.content_hash, one.text) for i in range(3)]
    monkeypatch.setattr(open_facts, "load_passages", lambda lake, d: three)
    monkeypatch.setattr(open_facts, "PASSAGES_PER_CALL", 2)
    client = TripleClient()
    out = open_facts.extract_doc(lake, client, "fake", doc_id)
    assert len(client.calls) == 2 and out["facts"] >= 3     # two passages, then one
    assert out["usage"]["inputTokens"] == 200 and open_facts.load_open_facts(lake, doc_id)["passages"] == 3


def test_no_facts_is_an_empty_list(lake):
    assert open_fact_rows(lake) == [] and open_facts.load_open_facts(lake, "nothing") is None
