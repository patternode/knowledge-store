"""examples/enterprise-rag-bench/fetch.py: which questions and documents it takes, and that the set it
writes is one the evaluation parses. Nothing is fetched."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from knowledge_store.evaluation.domain import score
from knowledge_store.evaluation.domain.sets import parse

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location("erb_fetch", ROOT / "examples/enterprise-rag-bench/fetch.py")
fetch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fetch)

INDEX = {
    "dsid_a": "confluence/sre/runbook-a.json",
    "dsid_b": "jira/ops/SUP-1.json",
    "dsid_c": "confluence/sre/runbook-c.json",
    "dsid_d": "confluence/sre/runbook-d.json",
    "dsid_e": "confluence/sre/runbook-e.json",
    "dsid_f": "slack/general/thread-f.json",
}
QUESTIONS = [
    {"question_id": "qst_0001", "question_type": "basic", "source_types": ["confluence"],
     "question": "What is the default TTL?", "expected_doc_ids": ["dsid_a"],
     "gold_answer": "120 seconds.", "answer_facts": ["The default TTL is 120 seconds."]},
    {"question_id": "qst_0411", "question_type": "conflicting_info", "source_types": ["confluence", "jira"],
     "question": "Which percentage applies now?", "expected_doc_ids": ["dsid_a", "dsid_b", "dsid_b"],
     "gold_answer": "30%, not the earlier 20%.", "answer_facts": ["The current figure is 30%."]},
    {"question_id": "qst_0471", "question_type": "high_level", "source_types": [],
     "question": "What are the company's themes this year?", "expected_doc_ids": [],
     "gold_answer": "Many.", "answer_facts": []},
    {"question_id": "qst_0481", "question_type": "info_not_found", "source_types": [],
     "question": "Which blockchain do we anchor to?", "expected_doc_ids": [],
     "gold_answer": "The answer must state that it is not answerable.", "answer_facts": ["Not answerable."]},
]


def test_high_level_questions_are_left_out_and_the_rest_keep_their_order():
    assert [q["question_id"] for q in fetch.selected(QUESTIONS)] == ["qst_0001", "qst_0411", "qst_0481"]


def test_gold_documents_are_the_paths_the_questions_cite_once_each():
    assert fetch.gold_paths(fetch.selected(QUESTIONS), INDEX) == ["confluence/sre/runbook-a.json", "jira/ops/SUP-1.json"]


def test_distractors_come_from_the_gold_documents_folders_and_are_stable():
    gold = ["confluence/sre/runbook-a.json", "jira/ops/SUP-1.json"]
    paths = list(INDEX.values())
    one = fetch.distractors(gold, paths, 1)
    assert len(one) == 1 and one[0].startswith("confluence/sre/") and one[0] not in gold
    assert fetch.distractors(gold, list(reversed(paths)), 1) == one
    assert fetch.distractors(gold, paths, 5) == ["confluence/sre/runbook-c.json", "confluence/sre/runbook-d.json",
                                                 "confluence/sre/runbook-e.json"]
    assert fetch.distractors(gold, paths, 0) == []


def test_the_written_set_parses_with_kinds_sources_and_declines():
    ev = parse(fetch.eval_set(QUESTIONS, INDEX, "redwood"))
    assert ev.collection == "redwood" and ev.name == "enterprise-rag-bench"
    by_id = {q.id: q for q in ev.questions}
    assert set(by_id) == {"qst_0001", "qst_0411", "qst_0481"}
    basic, conflict, absent = by_id["qst_0001"], by_id["qst_0411"], by_id["qst_0481"]
    assert basic.kind == "lookup" and basic.judged and basic.sources == ["confluence/sre/runbook-a.json"]
    assert conflict.sources == ["confluence/sre/runbook-a.json", "jira/ops/SUP-1.json"]
    assert conflict.context == {"question_type": "conflicting_info", "answer_facts": ["The current figure is 30%."]}
    assert absent.kind == "unanswerable" and not absent.answerable and not absent.sources


def test_a_cited_landing_key_hits_the_expected_document():
    q = parse(fetch.eval_set(QUESTIONS, INDEX, "redwood")).questions[0]
    result = {"answer": "The default TTL is 120 seconds. [1]", "abstained": False,
              "sources": [{"name": "landing/redwood/confluence/sre/runbook-a.json"}],
              "grounding": {"claims_proposed": 1, "claims_shown": 1}}
    assert score.score(q, result)["source_hit"]


def test_the_document_index_names_each_fetched_file_by_its_benchmark_id():
    index = {"dsid_b": "slack/eng/b.json", "dsid_a": "jira/a.json", "dsid_c": "jira/c.json"}
    assert fetch.document_index(["slack/eng/b.json", "jira/a.json"], index) == [
        {"doc_id": "dsid_a", "path": "jira/a.json"}, {"doc_id": "dsid_b", "path": "slack/eng/b.json"}]
