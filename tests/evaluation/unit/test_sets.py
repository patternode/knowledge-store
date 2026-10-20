"""The set model: parsing a set's YAML into questions, and refusing a set that cannot be scored."""

from __future__ import annotations

import pytest

from knowledge_store.evaluation.domain.sets import KINDS, EvalSet, Question, parse


def one(**q):
    return {"collection": "c", "questions": [{"id": "a", "question": "?", "must": ["x"], **q}]}


def test_a_set_keeps_its_collection_and_questions_in_order():
    ev = parse({"collection": "missions", "questions": [{"id": "b", "question": "?", "must": ["x"]},
                                                         {"id": "a", "question": "?", "must": ["y"]}]})
    assert isinstance(ev, EvalSet) and ev.collection == "missions" and [q.id for q in ev.questions] == ["b", "a"]


def test_the_name_in_the_file_wins_over_the_file_name():
    assert parse({**one(), "name": "named"}, name="file").name == "named"
    assert parse(one(), name="file").name == "file"


def test_a_single_spelling_becomes_a_list_of_one():
    assert parse(one(must=["Atlas V", ["Juno", "JUNO"]])).questions[0].must == [["Atlas V"], ["Juno", "JUNO"]]


def test_a_bare_figure_becomes_a_value():
    assert parse(one(must=[], figures=[2.2e9, {"value": 3, "tolerance": 0.1}])).questions[0].figures == \
        [{"value": 2.2e9}, {"value": 3, "tolerance": 0.1}]


def test_defaults_describe_an_answerable_public_lookup():
    q = parse(one()).questions[0]
    assert (q.kind, q.answerable, q.private, q.family, q.must_not, q.first, q.sources) == ("lookup", True, False, "", [], [], [])


def test_the_input_is_not_changed_by_parsing():
    data = one(must=["x"])
    parse(data)
    assert data["questions"][0]["must"] == ["x"]


def test_duplicate_ids_are_refused():
    with pytest.raises(ValueError, match="unique"):
        parse({"collection": "c", "questions": [{"id": "a", "question": "?", "must": ["x"]}] * 2})


def test_an_unknown_kind_is_refused():
    with pytest.raises(ValueError, match="kind must be one of"):
        parse(one(kind="trivia"))


def test_an_unanswerable_kind_must_say_it_is_unanswerable():
    with pytest.raises(ValueError, match="answerable: false"):
        parse(one(kind="unanswerable", must=[]))


def test_an_answerable_question_needs_a_fact_or_a_figure():
    with pytest.raises(ValueError, match="at least one fact"):
        parse(one(must=[]))
    assert parse(one(must=[], figures=[1])).questions[0].figures == [{"value": 1}]


def test_an_unanswerable_question_needs_no_fact():
    q = parse(one(kind="unanswerable", answerable=False, must=[])).questions[0]
    assert not q.answerable and q.must == []


def test_a_comparison_names_exactly_two_candidates():
    with pytest.raises(ValueError, match="two candidates"):
        parse(one(kind="comparison", first=["a", "b", "c"]))
    assert parse(one(kind="comparison", first=["a", "b"])).questions[0].first == ["a", "b"]


def test_a_figure_needs_a_numeric_value():
    with pytest.raises(ValueError, match="numeric value"):
        parse(one(figures=[{"value": "three"}]))


def test_an_unknown_field_is_refused():
    with pytest.raises(TypeError):
        parse(one(colour="red"))


def test_a_set_without_questions_is_refused():
    with pytest.raises(KeyError):
        parse({"collection": "c"})


def test_every_kind_is_accepted():
    for kind in KINDS:
        extra = {"answerable": False, "must": []} if kind == "unanswerable" else {}
        assert parse(one(kind=kind, **extra)).questions[0].kind == kind


def test_a_question_carries_its_structured_hint_untouched():
    hint = {"tool": "lookup_rows", "type": "Mission"}
    assert parse(one(structured=hint)).questions[0].structured == hint


def test_a_question_can_be_built_directly():
    q = Question(id="q", question="?")
    assert q.must == [] and q.figures == [] and q.structured is None
