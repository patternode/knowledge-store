"""Extraction domain: an extraction result as ontology-typed RDF with provenance."""

from __future__ import annotations

from rdflib import RDF, RDFS, XSD, Dataset, Literal, URIRef
from rdflib.namespace import SKOS

from extraction_spec import DOC_ID, doc, good_result, passages, run, spec
from knowledge_store.extraction.domain.rdf import Iris, build_graph, data_base, label_messages, slug, to_nquads
from knowledge_store.ontology import KL

NS = "https://example.org/missions#"


def _graph(**kw):
    return build_graph(good_result(), spec=spec(), doc=doc(), passages=passages(), run=run(), **kw)


def test_the_data_base_replaces_the_namespace_fragment_with_id():
    assert data_base(spec()) == "https://example.org/missions/id/"


def test_a_slug_is_lower_case_and_hyphenated():
    assert slug("  Mission Alpha (2011)! ") == "mission-alpha-2011"


def test_a_slug_is_capped_at_80_characters():
    assert len(slug("a" * 200)) == 80


def test_a_name_with_no_letters_or_digits_slugs_to_a_hash():
    assert slug("!!!") == slug("!!!") and len(slug("!!!")) == 12 and slug("!!!") != slug("???")


def test_an_entity_iri_is_keyed_by_its_root_class():
    ids = Iris(spec())
    assert ids.entity("Orbiter", "Alpha") == ids.entity("Mission", "Alpha")
    assert str(ids.entity("Mission", "Alpha")) == "https://example.org/missions/id/entity/Mission/alpha"


def test_iris_quote_unsafe_characters():
    assert str(Iris(spec()).passage("a b/c")) == "https://example.org/missions/id/passage/a%20b%2Fc"


def test_an_assertion_iri_depends_on_subject_predicate_and_object():
    ids = Iris(spec())
    assert ids.assertion("s", "p", "o") == ids.assertion("s", "p", "o") != ids.assertion("s", "p", "o2")


def test_graph_and_run_iris_name_their_parts():
    ids = Iris(spec())
    assert str(ids.graph("0.1.0", "d")).endswith("/graph/0.1.0/d")
    assert str(ids.run("r1")).endswith("/run/r1")
    assert str(ids.doc("d")).endswith("/doc/d")


def test_the_document_is_typed_labelled_and_scoped():
    g, _ = _graph()
    d = Iris(spec()).doc(DOC_ID)
    assert (d, RDF.type, KL.Document) in g
    assert g.value(d, RDFS.label) == Literal("Alpha")
    assert g.value(d, KL.scope) == Literal("public")


def test_an_untitled_document_has_no_label():
    g, _ = build_graph(good_result(), spec=spec(), doc={"doc_id": DOC_ID}, passages=passages(), run=run())
    assert g.value(Iris(spec()).doc(DOC_ID), RDFS.label) is None


def test_the_run_records_model_prompt_and_version():
    g, _ = _graph()
    r = Iris(spec()).run("r1")
    assert g.value(r, KL.modelId) == Literal("fake")
    assert g.value(r, KL.ontologyVersion) == Literal("0.1.0")
    assert g.value(r, KL.delta) is None


def test_a_delta_run_is_marked():
    g, _ = build_graph(good_result(), spec=spec(), doc=doc(), passages=passages(), run={**run(), "delta": True})
    assert g.value(Iris(spec()).run("r1"), KL.delta) == Literal(True)


def test_entities_are_typed_labelled_and_cited():
    g, where = _graph()
    alpha = Iris(spec()).entity("Mission", "Mission Alpha")
    assert (alpha, RDF.type, URIRef(NS + "Mission")) in g
    assert g.value(alpha, RDFS.label) == Literal("Mission Alpha")
    assert (alpha, KL.mentionedIn, Iris(spec()).passage(passages()[0].passage_id)) in g
    assert where[str(alpha)] == "entities[0]"


def test_aliases_become_alt_labels_without_blanks_or_the_name_itself():
    g, _ = _graph()
    alts = set(g.objects(Iris(spec()).entity("Mission", "Mission Alpha"), SKOS.altLabel))
    assert alts == {Literal("Alpha")}


def test_attributes_are_typed_literals_and_reified():
    g, where = _graph()
    alpha = Iris(spec()).entity("Mission", "Mission Alpha")
    year = Literal(2011, datatype=XSD.integer)
    assert (alpha, URIRef(NS + "launchYear"), year) in g
    a = Iris(spec()).assertion(alpha, URIRef(NS + "launchYear"), year)
    assert (a, RDF.type, KL.Assertion) in g and where[str(a)] == "attributes[0]"
    assert (a, KL.extractedBy, Iris(spec()).run("r1")) in g


def test_a_string_attribute_is_a_plain_literal():
    p = passages()
    r = good_result()
    r["attributes"] = [{"entity": "e1", "property": "motto", "value": "Reach further", "passage_ids": [p[-1].passage_id]}]
    g, _ = build_graph(r, spec=spec(), doc=doc(), passages=p, run=run())
    assert (Iris(spec()).entity("Mission", "Mission Alpha"), URIRef(NS + "motto"), Literal("Reach further")) in g


def test_relations_join_entities_and_are_reified():
    g, where = _graph()
    ids = Iris(spec())
    s, o = ids.entity("Mission", "Mission Alpha"), ids.entity("SpaceAgency", "Agency Nova")
    assert (s, URIRef(NS + "launchedBy"), o) in g
    assert where[str(ids.assertion(s, URIRef(NS + "launchedBy"), o))] == "relations[0]"


def test_only_cited_passages_are_written_with_their_document():
    g, _ = _graph()
    ids = Iris(spec())
    written = set(g.subjects(RDF.type, KL.Passage))
    assert written == {ids.passage(p.passage_id) for p in passages()[:2]}
    assert all((p, KL.partOf, ids.doc(DOC_ID)) in g for p in written)


def test_a_citation_of_an_unknown_passage_is_ignored():
    r = good_result()
    r["entities"][0]["passage_ids"].append("nope")
    g, _ = build_graph(r, spec=spec(), doc=doc(), passages=passages(), run=run())
    assert Iris(spec()).passage("nope") not in set(g.subjects())


def test_known_entities_can_be_referred_to_by_ref():
    r = {"entities": [], "attributes": [{"entity": "k1", "property": "launchYear", "value": "2011", "passage_ids": []}]}
    known = {"k1": {"iri": "https://example.org/missions/id/entity/Mission/x", "type": "Mission"}}
    g, _ = build_graph(r, spec=spec(), doc=doc(), passages=passages(), run=run(), known=known)
    assert (URIRef(known["k1"]["iri"]), URIRef(NS + "launchYear"), Literal(2011, datatype=XSD.integer)) in g


def test_messages_are_labelled_with_the_item_that_produced_them():
    where = {"https://x/n1": "entities[0]"}
    assert label_messages(["https://x/n1 p: bad", "other"], where) == ["entities[0] https://x/n1 p: bad", "other"]


def test_nquads_put_every_triple_in_the_named_graph():
    g, _ = _graph()
    gi = Iris(spec()).graph("0.1.0", DOC_ID)
    ds = Dataset()
    ds.parse(data=to_nquads(g, gi).decode(), format="nquads")
    assert len(ds.graph(gi)) == len(g)
