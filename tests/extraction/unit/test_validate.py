"""Extraction domain: the checks on an extraction result."""

from __future__ import annotations

import copy

from rdflib import Graph

from extraction_spec import good_result, passages, spec
from knowledge_store.extraction.domain import validate
from knowledge_store.extraction.domain.validate import clean_candidates, grounding_errors, norm, shape_errors


def test_norm_folds_typographic_quotes_dashes_spaces_and_case():
    assert norm("“It’s” –  A B") == "\"it's\" - a b"


def test_a_good_result_has_no_shape_errors():
    assert shape_errors(good_result(), spec()) == []


def test_a_result_that_is_not_an_object_is_refused():
    assert shape_errors([], spec()) == ["the result must be an object"]


def test_sections_must_be_lists():
    assert shape_errors({"entities": {}, "candidates": "x"}, spec()) == ["entities must be a list", "candidates must be a list"]


def test_an_entity_must_be_an_object():
    assert shape_errors({"entities": ["x"]}, spec()) == ["entities[0] must be an object"]


def test_an_entity_needs_a_ref_a_known_type_a_name_and_a_citation():
    errs = shape_errors({"entities": [{"type": "Rocket", "name": " ", "passage_ids": []}]}, spec())
    assert errs == ["entities[0] has no ref", "entities[0] type 'Rocket' is not an entity type in the ontology",
                    "entities[0] has no name", "entities[0] cites no passage"]


def test_a_ref_may_not_be_reused():
    r = good_result()
    r["entities"][1]["ref"] = "e1"
    assert "entities[1] reuses ref 'e1'; refs must be unique" in shape_errors(r, spec())


def test_a_ref_held_from_an_earlier_version_may_not_be_redeclared():
    r = good_result()
    assert "entities[0] reuses ref 'e1'; refs must be unique" in shape_errors(r, spec(), known={"e1": "Mission"})


def test_an_attribute_must_be_an_object():
    assert shape_errors({"attributes": [1]}, spec()) == ["attributes[0] must be an object"]


def test_an_attribute_must_name_a_property_in_the_ontology():
    r = good_result()
    r["attributes"][0]["property"] = "colour"
    assert shape_errors(r, spec()) == ["attributes[0] property 'colour' is not an attribute in the ontology"]


def test_an_attribute_must_name_a_declared_entity():
    r = good_result()
    r["attributes"][0]["entity"] = "e9"
    assert shape_errors(r, spec()) == ["attributes[0] names entity 'e9', which is not declared"]


def test_an_attribute_must_apply_to_its_entitys_type():
    r = good_result()
    r["attributes"][0]["entity"] = "e2"
    assert shape_errors(r, spec()) == ["attributes[0] launchYear applies to Mission, not SpaceAgency"]


def test_an_attribute_on_a_subclass_is_allowed():
    r = good_result()
    r["entities"][0]["type"] = "Orbiter"
    assert shape_errors(r, spec()) == []


def test_an_attribute_value_must_parse_as_its_datatype():
    r = good_result()
    r["attributes"][0]["value"] = "two thousand"
    errs = shape_errors(r, spec())
    assert len(errs) == 1 and errs[0].startswith("attributes[0] ")


def test_an_attribute_must_cite_a_passage():
    r = good_result()
    r["attributes"][0]["passage_ids"] = []
    assert shape_errors(r, spec()) == ["attributes[0] cites no passage"]


def test_a_relation_must_be_an_object():
    assert shape_errors({"relations": [None]}, spec()) == ["relations[0] must be an object"]


def test_a_relation_must_name_a_predicate_in_the_ontology():
    r = good_result()
    r["relations"][0]["predicate"] = "orbits"
    assert shape_errors(r, spec()) == ["relations[0] predicate 'orbits' is not a relation in the ontology"]


def test_a_relation_must_join_declared_entities():
    r = good_result()
    r["relations"][0]["object"] = "e9"
    assert shape_errors(r, spec()) == ["relations[0] subject 'e1' or object 'e9' is not declared"]


def test_a_relation_must_fit_its_signature():
    r = good_result()
    r["relations"][0]["object"] = "e3"
    assert shape_errors(r, spec()) == ["relations[0] launchedBy goes Mission -> SpaceAgency, not Mission -> TargetBody"]


def test_a_relation_must_cite_a_passage():
    r = good_result()
    r["relations"][0]["passage_ids"] = None
    assert shape_errors(r, spec()) == ["relations[0] cites no passage"]


def test_a_good_result_is_grounded():
    assert grounding_errors(good_result(), spec(), passages()) == []


def test_a_citation_of_a_missing_passage_is_reported():
    r = good_result()
    r["relations"][0]["passage_ids"] = ["nope"]
    assert grounding_errors(r, spec(), passages()) == ["relations[0] cites passages that do not exist: ['nope']"]


def test_an_entity_named_nowhere_in_its_passages_is_reported():
    r = good_result()
    r["entities"][1]["name"] = "Agency Orbis"
    assert grounding_errors(r, spec(), passages()) == [
        "entities[1] name 'Agency Orbis' does not appear in the passages it cites"]


def test_an_alias_in_the_passage_grounds_the_entity():
    r = good_result()
    r["entities"][1]["name"] = "The Nova agency"
    r["entities"][1]["aliases"] = ["Agency Nova"]
    assert grounding_errors(r, spec(), passages()) == []


def test_a_value_not_stated_is_reported():
    r = good_result()
    r["attributes"][0]["value"] = "2012"
    errs = grounding_errors(r, spec(), passages())
    assert errs == ["attributes[0] value '2012' is not stated in the passages it cites; copy it as written"]


def test_a_number_matches_without_its_thousands_separator_or_currency():
    r = good_result()
    r["attributes"][1]["value"] = "$1,250.50"
    assert grounding_errors(r, spec(), passages()) == []


def test_a_decimal_matches_without_trailing_zeros():
    r = good_result()
    r["attributes"][1]["value"] = "1250.5"
    assert grounding_errors(r, spec(), passages()) == []


def test_a_missing_passage_for_an_entity_or_attribute_is_reported_once_each():
    r = good_result()
    r["entities"][0]["passage_ids"] = ["x"]
    r["attributes"][0]["passage_ids"] = ["y"]
    errs = grounding_errors(r, spec(), passages())
    assert errs == ["entities[0] cites passages that do not exist: ['x']",
                    "attributes[0] cites passages that do not exist: ['y']"]


def test_a_string_value_must_be_stated_verbatim():
    p = passages()
    r = good_result()
    r["attributes"] = [{"entity": "e1", "property": "motto", "value": "\"Reach further\"", "passage_ids": [p[-1].passage_id]}]
    assert grounding_errors(r, spec(), p) == []
    r["attributes"][0]["value"] = "Reach farther"
    assert len(grounding_errors(r, spec(), p)) == 1


def _cand(**kw):
    c = {"kind": "class", "term": "Instrument", "evidence": "Agency Nova", "passage_ids": [passages()[0].passage_id]}
    return {**c, **kw}


def test_a_candidate_with_verbatim_evidence_is_kept():
    kept, dropped = clean_candidates({"candidates": [_cand()]}, passages())
    assert kept == [_cand()] and dropped == 0


def test_candidates_without_evidence_a_term_a_kind_or_a_real_passage_are_dropped():
    bad = [_cand(evidence="Agency Zed"), _cand(evidence=""), _cand(term=" "), _cand(kind="thing"),
           _cand(passage_ids=["nope"]), "not a dict"]
    kept, dropped = clean_candidates({"candidates": bad}, passages())
    assert kept == [] and dropped == len(bad)


def test_no_candidates_is_nothing_kept_and_nothing_dropped():
    assert clean_candidates({}, passages()) == ([], 0)


def test_the_value_reader_is_the_kernels():
    from knowledge_store.kernel.values import parse_value
    assert validate.parse_value is parse_value


def test_shacl_reports_a_violation_with_its_focus_node_and_message():
    shapes = Graph().parse(data="""
    @prefix sh: <http://www.w3.org/ns/shacl#> . @prefix ex: <https://example.org/> .
    ex:S a sh:NodeShape ; sh:targetClass ex:Thing ;
        sh:property [ sh:path ex:name ; sh:minCount 1 ; sh:message "a thing needs a name" ] .
    """, format="turtle")
    data = Graph().parse(data="<https://example.org/t1> a <https://example.org/Thing> .", format="turtle")
    ok, msgs, text = validate.shacl_errors(data, shapes, Graph())
    assert not ok and msgs == ["https://example.org/t1 https://example.org/name: a thing needs a name"] and text


def test_shacl_conforming_data_has_no_messages():
    ok, msgs, _ = validate.shacl_errors(Graph(), Graph(), Graph())
    assert ok and msgs == []


def test_checks_do_not_change_the_result():
    r = good_result()
    before = copy.deepcopy(r)
    shape_errors(r, spec())
    grounding_errors(r, spec(), passages())
    clean_candidates(r, passages())
    assert r == before
