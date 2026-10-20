"""Extraction slice: the extract, check, repair, salvage loop for one document, through a scripted
model client (the ModelClient port)."""

from __future__ import annotations

import copy

import pytest

from extraction_spec import doc, good_result, passages, run, spec
from knowledge_store.extraction.slices import extractor as ex
from knowledge_store.extraction.slices.extractor import (
    DELTA_NOTE, MAX_REPAIRS, ExtractionOutcome, Extractor, render_passages, run_record,
)
from knowledge_store.ingestion.domain.chunk import Passage
from knowledge_store.platform_services.slices.config import Profile


def _resp(payload, usage=None):
    return {"output": {"message": {"role": "assistant", "content": [
        {"text": "thinking"}, {"toolUse": {"toolUseId": "t1", "name": "record_knowledge", "input": payload}}]}},
        "stopReason": "tool_use", "usage": usage or {"inputTokens": 10, "outputTokens": 5}}


class Scripted:
    """A ModelClient that answers with the next scripted response, or raises it if it is an exception."""

    def __init__(self, *answers):
        self.answers, self.requests = list(answers), []

    def converse(self, **kw):
        self.requests.append(copy.deepcopy(kw))
        a = self.answers.pop(0)
        if isinstance(a, BaseException):
            raise a
        return a


def _extractor(client, **kw):
    return Extractor(client, "model-x", spec(), Profile(name="Missions"), **kw)


def test_a_valid_first_answer_is_kept_without_repair():
    client = Scripted(_resp(good_result()))
    out = _extractor(client).extract(doc(), passages(), run())
    assert isinstance(out, ExtractionOutcome)
    assert out.repairs == 0 and out.dropped == [] and out.result == good_result()
    assert out.usage == {"inputTokens": 10, "outputTokens": 5, "cacheReadInputTokens": 0, "cacheWriteInputTokens": 0}
    assert len(out.graph) > 0


def test_the_request_forces_the_tool_and_caches_the_system_prompt():
    client = Scripted(_resp(good_result()))
    _extractor(client).extract(doc(), passages(), run())
    req = client.requests[0]
    assert req["modelId"] == "model-x"
    assert req["toolConfig"]["toolChoice"] == {"tool": {"name": "record_knowledge"}}
    assert req["system"][1] == {"cachePoint": {"type": "default"}}
    assert req["inferenceConfig"]["temperature"] == 0
    assert "Missions" in req["system"][0]["text"] and "Mission" in req["system"][0]["text"]


def test_a_batch_request_has_no_cache_point():
    body = _extractor(Scripted()).request_body([], {"toolSpec": {}}, batch=True)
    assert body["system"] == [{"text": body["system"][0]["text"]}]


def test_the_first_message_names_the_document_and_numbers_its_passages():
    msgs = Extractor.first_messages(doc(), passages())
    text = msgs[0]["content"][0]["text"]
    assert text.startswith("Document: Alpha (source: docs).")
    assert all(f'<passage id="{p.passage_id}">' in text for p in passages())


def test_an_untitled_document_falls_back_to_its_name_then_its_id():
    assert "Document: f.txt" in Extractor.first_messages({"doc_id": "d", "name": "f.txt"}, [])[0]["content"][0]["text"]
    assert "Document: d (" in Extractor.first_messages({"doc_id": "d"}, [])[0]["content"][0]["text"]


def test_known_entities_are_listed_by_ref():
    text = Extractor.first_messages(doc(), [], {"k1": {"type": "Mission", "name": "Mission Alpha"}})[0]["content"][0]["text"]
    assert 'Known entities:\n- k1: Mission "Mission Alpha"' in text


def test_a_rejected_answer_is_sent_back_with_its_errors_and_repaired():
    bad = good_result()
    bad["attributes"][0]["value"] = "2012"
    client = Scripted(_resp(bad), _resp(good_result(), {"inputTokens": 1, "outputTokens": 1}))
    out = _extractor(client).extract(doc(), passages(), run())
    assert out.repairs == 1 and out.usage["inputTokens"] == 11
    repair = client.requests[1]["messages"]
    assert repair[1]["role"] == "assistant"
    result = repair[2]["content"][0]["toolResult"]
    assert result["status"] == "error" and result["toolUseId"] == "t1"
    assert "attributes[0] value '2012' is not stated" in result["content"][0]["text"]


def test_after_the_last_repair_the_bad_items_are_dropped_and_the_rest_kept():
    bad = good_result()
    bad["attributes"][0]["value"] = "2012"
    client = Scripted(*[_resp(bad)] * (MAX_REPAIRS + 1))
    out = _extractor(client).extract(doc(), passages(), run())
    assert out.repairs == MAX_REPAIRS and out.dropped == ["attributes[0]"]
    assert len(out.result["attributes"]) == 1 and len(out.result["relations"]) == 2
    assert len(client.requests) == MAX_REPAIRS + 1


def test_dropping_an_entity_drops_what_hangs_off_it():
    bad = good_result()
    bad["entities"][1]["name"] = "Agency Zed"  # not in its passage
    client = Scripted(*[_resp(bad)] * (MAX_REPAIRS + 1))
    out = _extractor(client).extract(doc(), passages(), run())
    assert out.dropped == ["entities[1]"]
    assert [e["ref"] for e in out.result["entities"]] == ["e1", "e3"]
    assert [r["predicate"] for r in out.result["relations"]] == ["studies"]


def test_an_answer_that_cannot_be_salvaged_fails_the_document():
    client = Scripted(*[_resp({"entities": "x"})] * (MAX_REPAIRS + 1))  # a section error names no item
    with pytest.raises(ValueError, match="still invalid after salvage"):
        _extractor(client).extract(doc(), passages(), run())


def test_a_non_object_tool_input_is_an_empty_answer():
    out = _extractor(Scripted(_resp("[]"))).extract(doc(), passages(), run())
    assert out.result == {} and out.repairs == 0


def test_a_supplied_first_response_is_used_without_calling_the_model():
    client = Scripted()
    out = _extractor(client).extract(doc(), passages(), run(), first_response=_resp(good_result()))
    assert client.requests == [] and out.repairs == 0


def test_an_answer_without_a_tool_call_fails():
    resp = {"output": {"message": {"content": [{"text": "no"}]}}, "stopReason": "end_turn"}
    with pytest.raises(RuntimeError, match="did not call the extraction tool"):
        _extractor(Scripted(resp)).extract(doc(), passages(), run())


class ThrottlingException(Exception):
    pass


def test_throttling_is_retried_after_a_pause(monkeypatch):
    slept = []
    monkeypatch.setattr(ex.time, "sleep", slept.append)
    client = Scripted(ThrottlingException("slow down"), _resp(good_result()))
    out = _extractor(client).extract(doc(), passages(), run())
    assert out.repairs == 0 and len(slept) == 1


def test_persistent_throttling_gives_up(monkeypatch):
    monkeypatch.setattr(ex.time, "sleep", lambda s: None)
    client = Scripted(*[RuntimeError("ServiceUnavailable: Throttling")] * ex.THROTTLE_ATTEMPTS)
    with pytest.raises(RuntimeError, match="throttled"):
        _extractor(client).extract(doc(), passages(), run())


def test_another_model_error_is_raised_at_once():
    with pytest.raises(PermissionError):
        _extractor(Scripted(PermissionError("denied"))).extract(doc(), passages(), run())


def test_candidates_are_kept_only_with_verbatim_evidence():
    r = good_result()
    pid = passages()[0].passage_id
    r["candidates"] = [{"kind": "class", "term": "Agency", "evidence": "Agency Nova", "passage_ids": [pid]},
                       {"kind": "class", "term": "Rocket", "evidence": "a big rocket", "passage_ids": [pid]}]
    out = _extractor(Scripted(_resp(r))).extract(doc(), passages(), run())
    assert [c["term"] for c in out.candidates] == ["Agency"]


def test_a_delta_extractor_adds_the_delta_note_and_limits_the_vocabulary():
    e = _extractor(Scripted(), only={"budget"})
    assert e.system.endswith(DELTA_NOTE) and "launchedBy" not in e.system and "budget" in e.system


def test_a_versions_own_shapes_are_applied_with_the_core_shapes():
    from rdflib import Graph
    shapes = Graph().parse(data="""
    @prefix sh: <http://www.w3.org/ns/shacl#> . @prefix o: <https://example.org/missions#> .
    o:NeedsYear a sh:NodeShape ; sh:targetClass o:Mission ;
        sh:property [ sh:path o:launchYear ; sh:minCount 1 ; sh:message "a mission needs a launch year" ] .
    """, format="turtle")
    r = good_result()
    r["attributes"] = [a for a in r["attributes"] if a["property"] != "launchYear"]
    client = Scripted(*[_resp(r)] * (MAX_REPAIRS + 1))
    out = _extractor(client, shapes=shapes).extract(doc(), passages(), run())
    assert out.dropped == ["entities[0]"]
    assert "a mission needs a launch year" in client.requests[1]["messages"][2]["content"][0]["toolResult"]["content"][0]["text"]


def test_a_result_that_cannot_become_rdf_is_sent_back_as_an_error():
    incomplete_run = {"run_id": "r"}  # no model id: the graph cannot be built
    client = Scripted(*[_resp(good_result())] * (MAX_REPAIRS + 1))
    with pytest.raises(ValueError, match="could not be converted"):
        Extractor.extract(_extractor(client), doc(), passages(), incomplete_run)


def test_render_passages_truncates_past_the_input_limit(monkeypatch):
    monkeypatch.setattr(ex, "MAX_INPUT_CHARS", 60)
    ps = [Passage(f"p{i}", "d", i, 0, 1, "h", "x" * 20) for i in range(3)]
    out = render_passages(ps)
    assert out.count("<passage") == 1 and out.endswith("<truncated/>")


def test_a_run_record_names_model_prompt_and_version():
    rec = run_record("r1", "m", "0.2.0", delta=True)
    assert rec == {"run_id": "r1", "model_id": "m", "prompt_version": ex.PROMPT_VERSION,
                   "ontology_version": "0.2.0", "delta": True}
