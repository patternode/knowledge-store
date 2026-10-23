"""The values vocabulary is the datatype list, not a parent of domain classes."""

from rdflib import Graph, Namespace, OWL, RDF, RDFS

from knowledge_store.ontology.domain.model import DATATYPES, KV, VALUES_TTL

TIME = Namespace("http://www.w3.org/2006/time#")


def test_the_file_parses_and_names_the_interval_datatype_and_the_unit():
    graph = Graph()
    graph.parse(VALUES_TTL, format="turtle")
    assert (KV.interval, RDF.type, RDFS.Datatype) in graph
    assert (KV.Interval, RDF.type, OWL.Class) in graph
    assert (KV.unit, RDF.type, OWL.AnnotationProperty) in graph
    assert (KV.interval, RDFS.seeAlso, TIME.Interval) in graph
    assert any(str(item).endswith("hasUnit") for item in graph.objects(KV.unit, RDFS.seeAlso))


def test_the_datatype_list_uses_the_vocabulary_for_an_interval_only():
    assert DATATYPES["date"] != DATATYPES["dateTime"]
    assert str(DATATYPES["duration"]).endswith("#duration")
    assert DATATYPES["interval"] == KV.interval
    assert "dateTime" in DATATYPES and "duration" in DATATYPES
