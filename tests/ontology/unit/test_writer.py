"""ontology.domain.writer: a definition written as Turtle a person can edit, and its SHACL."""

import pytest
from rdflib import Graph

from knowledge_store.ontology.domain import model, writer
from ks_ontology_sample import spec

NS = "https://example.org/new#"


@pytest.mark.parametrize("raw,name", [("space agency", "SpaceAgency"), ("launchYear", "LaunchYear"), ("3d model", "T3dModel"), ("a-b_c", "ABC")])
def test_class_name_is_upper_camel_case_and_starts_with_a_letter(raw, name):
    assert writer.class_name(raw) == name


def test_property_name_is_lower_camel_case():
    assert writer.property_name("launched by") == "launchedBy"


def test_normalise_resolves_references_and_drops_unknown_ones():
    d = writer.normalise_definition({
        "classes": [{"name": "mission"}, {"name": "Mission"}, {"name": "crewed mission", "parent": "mission"}, {"name": "x", "parent": "x"}, {"name": "y", "parent": "ghost"}],
        "relations": [{"name": "studies", "domain": "mission", "range": ["target", "mission"]}, {"name": "mission"}],
        "attributes": [{"name": "launch year", "domain": ["mission"], "datatype": "integer"}, {"name": "colour", "datatype": "rgb"}, {"name": "studies"}]})
    names = [c["name"] for c in d["classes"]]
    assert names == ["Mission", "CrewedMission", "X", "Y"]
    assert [c["parent"] for c in d["classes"]] == [None, "Mission", None, None]
    assert d["relations"][0] == {"name": "studies", "domain": ["Mission"], "range": ["Mission"]}
    assert [r["name"] for r in d["relations"]] == ["studies", "mission"]  # lower camel case: no clash with the class
    assert [(a["name"], a["datatype"]) for a in d["attributes"]] == [("launchYear", "integer"), ("colour", "string")]


def test_written_turtle_parses_back_into_the_same_terms():
    defn = {"classes": [{"name": "Mission", "label": "Mission", "definition": 'A "flight"\nup', "synonyms": ["sortie", "Mission"]}, {"name": "Agency"}],
            "relations": [{"name": "launchedBy", "domain": "Mission", "range": "Agency"}],
            "attributes": [{"name": "launchYear", "domain": "Mission", "datatype": "integer"}]}
    ttl = writer.ontology_ttl(defn, namespace=NS, version="0.1.0", label="New", evidence={"Mission": 3})
    s = model.load(data=ttl)
    assert s.version == "0.1.0" and set(s.classes) == {"Mission", "Agency"}
    assert s.classes["Mission"].alt_labels == ("sortie",) and s.classes["Mission"].definition == 'A "flight" up'
    assert s.relations["launchedBy"].range == ("Agency",) and s.attributes["launchYear"].range == ("integer",)
    assert "# seen in 3 documents" in ttl


def test_a_revision_keeps_the_prior_terms_and_adds_synonyms_only_to_them():
    prior = spec()
    defn = {"classes": [{"name": "Mission", "synonyms": ["sortie"], "definition": "changed"}, {"name": "Rover", "parent": "Mission"}]}
    ttl = writer.ontology_ttl(defn, namespace=prior.namespace, version="1.3.0", label="Space", prior=prior)
    s = model.load(data=ttl)
    assert {"SpaceAgency", "Mission", "Rover", "Target"} <= set(s.classes)
    assert s.classes["Mission"].alt_labels == ("sortie",) and s.classes["Mission"].definition == "A flight."
    assert s.classes["Rover"].parents == ("Mission",) and s.prior_version.endswith("/1.2.0")
    assert s.attributes["launchYear"].range == ("integer",)


def test_a_quantity_and_an_interval_are_written_with_the_values_vocabulary():
    defn = {"classes": [{"name": "Mission"}],
            "attributes": [
                {"name": "cost", "domain": "Mission", "datatype": "decimal",
                 "unit": "http://qudt.org/vocab/unit/USD"},
                {"name": "window", "domain": "Mission", "datatype": "interval", "unit": "days"},
                {"name": "liftoff", "domain": "Mission", "datatype": "dateTime"}]}
    ttl = writer.ontology_ttl(defn, namespace=NS, version="0.1.0", label="New")
    s = model.load(data=ttl)
    assert s.attributes["cost"].unit == "http://qudt.org/vocab/unit/USD"
    assert s.attributes["window"].range == ("interval",) and s.attributes["window"].unit == ""
    assert s.attributes["liftoff"].range == ("dateTime",)
    assert "kv:unit <http://qudt.org/vocab/unit/USD>" in ttl
    assert "sh:datatype kv:interval" in writer.shapes_ttl(s)
    assert "sh:datatype xsd:dateTime" in writer.shapes_ttl(s)


def test_a_relation_to_a_quantity_imports_the_measures_ontology_and_does_not_redeclare_it():
    defn = {"classes": [{"name": "Book"}, {"name": "Quantity", "definition": "should be dropped"}],
            "relations": [{"name": "pricedAt", "domain": "Book", "range": "Quantity"}]}
    ttl = writer.ontology_ttl(defn, namespace=NS, version="0.1.0", label="Books")
    assert "owl:imports <https://w3id.org/knowledge-store/measures>" in ttl
    assert "rdfs:range km:Quantity" in ttl and "o:Quantity" not in ttl
    s = model.load(data=ttl)
    assert s.classes["Book"].iri.startswith("https://example.org/new")
    assert s.classes["Quantity"].iri == "https://w3id.org/knowledge-store/measures#Quantity"
    assert s.relations["pricedAt"].range == ("Quantity",)
    assert "numericValue" in s.attributes and "km:Quantity" in writer.shapes_ttl(s)
    assert "o:numericValue" not in writer.shapes_ttl(s)


def test_shapes_check_single_ranges_and_every_attribute_and_parse():
    shapes = writer.shapes_ttl(spec())
    Graph().parse(data=shapes, format="turtle")
    assert "o:launchedByRangeShape" in shapes and "sh:class o:Organisation" in shapes
    assert "o:launchYearDatatypeShape" in shapes and "sh:datatype xsd:integer" in shapes
    assert "sh:datatype xsd:string" in shapes
