"""ontology.domain.tool_schema: the extraction tool call, generated from the ontology."""

from knowledge_store.ontology.domain import model
from knowledge_store.ontology.domain.tool_schema import TOOL_NAME, tool_spec
from ks_ontology_sample import spec


def _props(t):
    return t["toolSpec"]["inputSchema"]["json"]["properties"]


def test_the_tool_has_its_name_and_requires_entities_and_candidates():
    t = tool_spec(spec())
    assert t["toolSpec"]["name"] == TOOL_NAME
    assert t["toolSpec"]["inputSchema"]["json"]["required"] == ["entities", "candidates"]


def test_entity_types_attributes_and_relations_are_enumerated_from_the_ontology():
    p = _props(tool_spec(spec()))
    assert p["entities"]["items"]["properties"]["type"]["enum"] == ["CrewedMission", "Mission", "Organisation", "SpaceAgency", "Target"]
    assert p["relations"]["items"]["properties"]["predicate"]["enum"] == ["launchedBy", "studies"]
    assert p["attributes"]["items"]["properties"]["property"]["enum"] == ["budget", "launchYear", "motto"]


def test_every_list_cites_passages():
    p = _props(tool_spec(spec()))
    for k in ("entities", "attributes", "relations", "candidates"):
        assert p[k]["items"]["properties"]["passage_ids"]["minItems"] == 1


def test_candidates_are_classes_relations_or_attributes():
    assert _props(tool_spec(spec()))["candidates"]["items"]["properties"]["kind"]["enum"] == ["class", "relation", "attribute"]


def test_an_ontology_without_properties_asks_for_entities_and_candidates_only():
    p = _props(tool_spec(model.empty()))
    assert set(p) == {"entities", "candidates"} and p["entities"]["items"]["properties"]["type"]["enum"] == []


def test_a_delta_run_lists_the_focus_properties_and_the_classes_they_reference():
    p = _props(tool_spec(spec(), only={"studies", "launchYear"}))
    assert p["relations"]["items"]["properties"]["predicate"]["enum"] == ["studies"]
    assert p["attributes"]["items"]["properties"]["property"]["enum"] == ["launchYear"]
    assert p["entities"]["items"]["properties"]["type"]["enum"] == ["Mission", "Target"]


def test_a_delta_run_on_a_class_keeps_that_class():
    p = _props(tool_spec(spec(), only={"Target"}))
    assert p["entities"]["items"]["properties"]["type"]["enum"] == ["Target"]
    assert "relations" not in p and "attributes" not in p


def test_a_delta_run_naming_nothing_known_falls_back_to_every_class():
    p = _props(tool_spec(spec(), only={"nothing"}))
    assert len(p["entities"]["items"]["properties"]["type"]["enum"]) == 5


def test_known_refs_are_offered_as_endpoints():
    p = _props(tool_spec(spec(), known_refs=["k1", "k2"]))
    assert "k1" in p["relations"]["items"]["properties"]["subject"]["description"]
