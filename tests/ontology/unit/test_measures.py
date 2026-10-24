"""The measures ontology is the base a domain ontology imports."""

import pytest
from rdflib import Graph, Namespace, OWL, RDF, RDFS

from knowledge_store.ontology.domain.model import (
    FOUNDATION_CLASSES, MEASURES_NS, MEASURES_TTL, load,
)
from knowledge_store.ontology.slices.discover import DEFINE_SYSTEM

QUDT = Namespace("http://qudt.org/schema/qudt/")
TIME = Namespace("http://www.w3.org/2006/time#")


def test_the_file_parses_and_aligns_quantity_and_time_to_the_standards():
    graph = Graph()
    graph.parse(MEASURES_TTL, format="turtle")
    km = Namespace(MEASURES_NS)
    assert (km.Metric, RDFS.seeAlso, QUDT.QuantityKind) in graph
    assert (km.Quantity, RDFS.seeAlso, QUDT.Quantity) in graph
    assert (km.numericValue, RDFS.seeAlso, QUDT.numericValue) in graph
    assert (km.unit, RDFS.seeAlso, QUDT.hasUnit) in graph
    assert (km.Instant, RDFS.seeAlso, TIME.Instant) in graph
    assert (km.Period, RDFS.seeAlso, TIME.Interval) in graph
    assert (km.beginning, RDFS.seeAlso, TIME.hasBeginning) in graph
    assert (km.onDate, RDFS.seeAlso, TIME.inXSDDate) in graph
    assert (km.Metric, RDF.type, OWL.Class) in graph


def test_loading_it_gives_the_four_classes_and_the_value_kinds():
    spec = load(MEASURES_TTL)
    assert spec.version == "1.0.0" and set(spec.classes) == set(FOUNDATION_CLASSES)
    assert spec.attributes["numericValue"].range == ("decimal",)
    assert spec.attributes["unit"].range == ("anyURI",)
    assert spec.attributes["onDate"].range == ("date",)
    assert spec.attributes["atTime"].range == ("dateTime",)
    assert spec.attributes["duration"].range == ("duration",)
    assert spec.attributes["interval"].range == ("interval",)
    assert spec.relations["valueOf"].range == ("Metric",)
    assert spec.relations["during"].range == ("Period",)
    assert spec.relations["at"].range == ("Instant",)


def test_a_domain_ontology_that_imports_it_keeps_its_own_version_and_gains_the_four_classes():
    ttl = """
    @prefix o: <https://example.org/books#> .
    @prefix owl: <http://www.w3.org/2002/07/owl#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    @prefix km: <https://w3id.org/knowledge-store/measures#> .
    <https://example.org/books> a owl:Ontology ; owl:versionInfo "1.2.3" ;
        owl:imports <https://w3id.org/knowledge-store/measures> .
    o:Book a owl:Class .
    o:pricedAt a owl:ObjectProperty ; rdfs:domain o:Book ; rdfs:range km:Quantity .
    """
    spec = load(data=ttl)
    assert spec.version == "1.2.3" and spec.namespace == "https://example.org/books#"
    assert {"Book", "Quantity", "Metric", "Instant", "Period"} <= set(spec.classes)
    assert spec.relations["pricedAt"].range == ("Quantity",)
    assert "Quantity" in spec.vocabulary_prompt()


def test_a_domain_class_that_reuses_a_measure_name_is_refused():
    ttl = """
    @prefix o: <https://example.org/books#> .
    @prefix owl: <http://www.w3.org/2002/07/owl#> .
    <https://example.org/books> a owl:Ontology ; owl:versionInfo "1.0.0" ;
        owl:imports <https://w3id.org/knowledge-store/measures> .
    o:Quantity a owl:Class .
    """
    with pytest.raises(ValueError, match="Quantity"):
        load(data=ttl)


def test_discovery_is_told_to_use_the_measures_classes_and_not_to_redeclare_them():
    assert "measures ontology" in DEFINE_SYSTEM
    assert "Do not declare them again" in DEFINE_SYSTEM


def test_a_domain_property_keeps_a_name_a_measures_property_also_uses():
    ttl = """
    @prefix o: <https://example.org/ops#> .
    @prefix owl: <http://www.w3.org/2002/07/owl#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
    @prefix km: <https://w3id.org/knowledge-store/measures#> .
    <https://example.org/ops> a owl:Ontology ; owl:versionInfo "1.0.0" ;
        owl:imports <https://w3id.org/knowledge-store/measures> .
    o:Incident a owl:Class .
    o:duration a owl:DatatypeProperty ; rdfs:domain o:Incident ; rdfs:range xsd:string .
    o:at a owl:ObjectProperty ; rdfs:domain o:Incident ; rdfs:range km:Instant .
    o:end a owl:DatatypeProperty ; rdfs:domain o:Incident ; rdfs:range xsd:date .
    """
    spec = load(data=ttl)
    assert spec.attributes["duration"].iri == "https://example.org/ops#duration"
    assert spec.relations["at"].iri == "https://example.org/ops#at" and spec.relations["at"].range == ("Instant",)
    assert spec.attributes["end"].iri == "https://example.org/ops#end" and "end" not in spec.relations
    assert {"Incident", "Period", "Quantity"} <= set(spec.classes)
    assert spec.attributes["numericValue"].iri.startswith(MEASURES_NS)


def test_two_domain_terms_with_one_name_are_still_refused():
    ttl = """
    @prefix o: <https://example.org/ops#> .
    @prefix owl: <http://www.w3.org/2002/07/owl#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
    <https://example.org/ops> a owl:Ontology ; owl:versionInfo "1.0.0" ;
        owl:imports <https://w3id.org/knowledge-store/measures> .
    o:Incident a owl:Class .
    o:Incident a owl:DatatypeProperty ; rdfs:range xsd:string .
    """
    with pytest.raises(ValueError, match="Incident"):
        load(data=ttl)
