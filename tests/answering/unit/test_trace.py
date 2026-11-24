"""The answer trace, built from what the agent returned."""

from knowledge_store.answering import trace

OUT = {"answer": "An Atlas V [1]", "abstained": False, "outcome": "answered", "collection": "m",
       "ontology_version": "1.2.0", "toolset": "all",
       "claims": [{"text": "An Atlas V", "support": "supported", "verifier": "lexical", "support_score": 1.0,
                   "citations": [{"passage_id": "p1", "quote": "launched on an Atlas V"}]}],
       "retrieved": [{"tool": "search_passages", "kind": "passages", "rank": 1, "id": "p1"},
                     {"tool": "search_passages", "kind": "passages", "rank": 2, "id": "p2"}],
       "grounding": {"unsupported_dropped": [{"text": "x"}], "guardrail_dropped": [], "failures": []},
       "usage": {"inputTokens": 10}, "ms": 1200}


def build(out=OUT, **kw):
    args = dict(answer_id="a1", at="2026-11-24T10:00:00+00:00", question="Which rocket?", collection="m", out=out,
                caller=trace.caller_hash("user-1", "salt"), scopes=["public"], model="m", prompt_version=None,
                release="0.9.0")
    return trace.build(**{**args, **kw})


def test_a_trace_names_what_was_retrieved_cited_and_concluded():
    t = build()
    assert t["schema"] == "answer-trace/1" and t["outcome"] == "answered"
    assert [r["id"] for r in t["retrieved"]] == ["p1", "p2"] and t["cited"] == ["p1"]
    assert t["claims"][0]["support"] == "supported" and t["dropped"]["unsupported"] == 1
    assert t["ontology_version"] == "1.2.0" and t["release"] == "0.9.0"


def test_the_caller_is_a_keyed_hash_never_the_identity():
    t = build()
    assert t["caller"] and "user-1" not in t["caller"]
    assert trace.caller_hash("user-1", "salt") != trace.caller_hash("user-1", "other")
    assert trace.caller_hash(None, "salt") is None


def test_a_failure_is_traced_as_a_failure():
    t = build(out={"answer": "", "abstained": False, "outcome": "failed", "error": "The question could not be answered."})
    assert t["outcome"] == "failed" and t["claims"] == [] and t["retrieved"] == []
