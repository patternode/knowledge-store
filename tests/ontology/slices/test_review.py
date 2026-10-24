"""ontology.slices.review: a second look at a draft, returned as edits applied deterministically."""

import json

import pytest

from knowledge_store.ontology.slices import review
from knowledge_store.platform_services.slices.config import Profile
from ks_ontology_lake import ScriptedClient


def _draft():
    return {"classes": [{"name": "Body"}, {"name": "Planet", "parent": "Body"}, {"name": "Moon", "parent": "Planet"},
                        {"name": "Agency"}, {"name": "Space agency"}],
            "relations": [{"name": "orbits", "domain": "Moon", "range": "Planet"}, {"name": "runBy", "domain": "Planet", "range": "Agency"}],
            "attributes": [{"name": "mass", "domain": "Planet", "datatype": "decimal"}]}


def _apply(*edits):
    return review.apply_edits(_draft(), list(edits))


def _cls(d, name):
    return next(c for c in d["classes"] if c["name"] == name)


def test_the_draft_view_shows_document_support_per_term():
    agg = {"classes": [{"name": "planet", "also": ["Planets"], "docs": 4}]}
    view = json.loads(review.draft_view(_draft(), agg))
    assert _cls(view, "Planet")["docs"] == 4 and _cls(view, "Moon")["docs"] is None
    assert view["relations"][0]["domain"] == "Moon" and view["attributes"][0]["datatype"] == "decimal"


def test_review_returns_the_models_edits_and_drops_junk():
    client = ScriptedClient({"edits": [{"op": "drop", "kind": "classes", "term": "Moon"}, "junk"]})
    edits, usage = review.review(client, "m", _draft(), None, Profile())
    assert edits == [{"op": "drop", "kind": "classes", "term": "Moon"}] and usage["outputTokens"] == 2


def test_the_draft_given_is_never_changed():
    d = _draft()
    review.apply_edits(d, [{"op": "drop", "kind": "classes", "term": "Planet"}])
    assert d == _draft()


def test_set_parent_moves_a_class_and_null_makes_it_a_root():
    d, applied, _ = _apply({"op": "set_parent", "kind": "classes", "term": "agency", "value": "Body"},
                           {"op": "set_parent", "kind": "classes", "term": "Planet", "value": "null"})
    assert _cls(d, "Agency")["parent"] == "Body" and _cls(d, "Planet")["parent"] is None and len(applied) == 2


@pytest.mark.parametrize("edit,why", [
    ({"op": "rename", "kind": "classes", "term": "Body"}, "unknown op"),
    ({"op": "drop", "kind": "things", "term": "Body"}, "unknown op or kind"),
    ({"op": "drop", "kind": "classes", "term": "Ghost"}, "named 'Ghost'"),
    ({"op": "set_parent", "kind": "relations", "term": "orbits", "value": "Body"}, "applies to classes"),
    ({"op": "set_parent", "kind": "classes", "term": "Body", "value": "Ghost"}, "no class named"),
    ({"op": "set_parent", "kind": "classes", "term": "Body", "value": "Moon"}, "cycle"),
    ({"op": "set_parent", "kind": "classes", "term": "Body", "value": "Body"}, "cycle"),
    ({"op": "merge", "kind": "classes", "term": "Agency", "value": "Agency"}, "to merge into"),
    ({"op": "set_domain", "kind": "classes", "term": "Body", "value": "Body"}, "does not apply"),
    ({"op": "set_range", "kind": "attributes", "term": "mass", "value": "Body"}, "does not apply"),
    ({"op": "set_domain", "kind": "relations", "term": "orbits", "value": "Ghost"}, "no class named"),
    ({"op": "set_datatype", "kind": "classes", "term": "Body", "value": "integer"}, "applies to attributes"),
    ({"op": "set_datatype", "kind": "attributes", "term": "mass", "value": "colour"}, "is not one of"),
])
def test_an_edit_that_cannot_apply_is_skipped_with_why(edit, why):
    d, applied, skipped = _apply(edit)
    assert applied == [] and why in skipped[0]["skipped"] and d == {**_draft(), **{}}


def test_merge_folds_a_term_into_another_and_repoints_references():
    d, _, _ = _apply({"op": "merge", "kind": "classes", "term": "Agency", "value": "space agency"})
    sa = _cls(d, "Space agency")
    assert "Agency" in sa["synonyms"] and sa["merged_from"] == ["Agency"]
    assert [c["name"] for c in d["classes"]].count("Agency") == 0
    assert d["relations"][1]["range"] == "Space agency"


def test_dropping_a_class_drops_what_depends_on_it():
    d, applied, _ = _apply({"op": "drop", "kind": "classes", "term": "Planet"})
    assert [r["name"] for r in d["relations"]] == [] and d["attributes"] == []
    assert any("dropped relation orbits" in e for e in applied[0]["effects"])


def test_dropping_a_class_lifts_its_children_to_its_parent():
    d, _, _ = _apply({"op": "drop", "kind": "classes", "term": "Planet"})
    assert _cls(d, "Moon")["parent"] == "Body"


def test_a_skip_reason_names_the_kind_in_the_singular():
    _, _, skipped = _apply({"op": "drop", "kind": "classes", "term": "Ghost"})
    assert skipped[0]["skipped"] == "no class named 'Ghost'"


def test_dropping_a_relation_removes_only_it():
    d, _, _ = _apply({"op": "drop", "kind": "relations", "term": "orbits"})
    assert [r["name"] for r in d["relations"]] == ["runBy"]


def test_set_domain_range_and_datatype():
    d, applied, _ = _apply({"op": "set_domain", "kind": "attributes", "term": "mass", "value": "body"},
                           {"op": "set_range", "kind": "relations", "term": "orbits", "value": "Body"},
                           {"op": "set_datatype", "kind": "attributes", "term": "mass", "value": "integer"})
    assert d["attributes"][0] == {"name": "mass", "domain": "Body", "datatype": "integer"}
    assert d["relations"][0]["range"] == "Body" and len(applied) == 3


def test_a_later_edit_sees_an_earlier_one():
    _, applied, skipped = _apply({"op": "drop", "kind": "classes", "term": "Moon"}, {"op": "set_parent", "kind": "classes", "term": "Moon", "value": "Body"})
    assert len(applied) == 1 and "named 'Moon'" in skipped[0]["skipped"]


def test_a_relation_may_point_at_a_measure_without_declaring_it():
    d, applied, skipped = _apply({"op": "set_range", "kind": "relations", "term": "orbits", "value": "Quantity"})
    assert not skipped and len(applied) == 1
    assert next(r for r in d["relations"] if r["name"] == "orbits")["range"] == "Quantity"
    assert all(c["name"] != "Quantity" for c in d["classes"])


def test_a_draft_missing_a_kind_is_completed():
    d, _, _ = review.apply_edits({"classes": [{"name": "A"}]}, [])
    assert d == {"classes": [{"name": "A"}], "relations": [], "attributes": []}
