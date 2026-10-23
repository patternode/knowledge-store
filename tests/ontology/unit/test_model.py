"""ontology.domain.model: the spec every other step derives from."""

import pytest

from knowledge_store.ontology.domain import model
from ks_ontology_sample import TTL, spec


@pytest.fixture(scope="module")
def s():
    return spec()


def test_local_name_is_after_the_hash_or_the_last_slash():
    assert model.local_name("https://e.org/x#Mission") == "Mission"
    assert model.local_name("https://e.org/x/Mission/") == "Mission"


def test_the_ontology_header_is_read(s):
    assert (s.namespace, s.version, s.label, s.comment) == ("https://example.org/space#", "1.2.0", "Space", "Missions and who flies them.")
    assert s.version_iri.endswith("/1.2.0") and s.prior_version.endswith("/1.1.0")


def test_only_terms_in_the_ontology_namespace_are_read(s):
    assert "Thing" not in s.classes


def test_deprecated_terms_are_left_out(s):
    assert "Retired" not in s.classes


def test_english_labels_are_preferred(s):
    assert s.classes["SpaceAgency"].label == "Space agency"


def test_a_term_without_a_label_is_named_by_its_local_name(s):
    assert s.classes["CrewedMission"].label == "CrewedMission"


def test_definition_comes_from_skos_definition_or_rdfs_comment(s):
    assert s.classes["SpaceAgency"].definition == "A body that runs space programmes."
    assert s.classes["Mission"].definition == "A flight."


def test_parents_are_in_namespace_superclasses(s):
    assert s.classes["SpaceAgency"].parents == ("Organisation",)


def test_relations_have_domain_and_range(s):
    r = s.relations["launchedBy"]
    assert (r.kind, r.domain, r.range) == ("relation", ("Mission",), ("Organisation",))


def test_attributes_have_a_value_kind(s):
    assert s.attributes["launchYear"].range == ("integer",)
    assert s.attributes["budget"].range == ("decimal",)
    assert s.attributes["motto"].range == ("string",) and s.attributes["motto"].domain == ()


def test_a_date_and_time_is_not_read_as_a_date_and_a_quantity_keeps_its_unit():
    ttl = """
    @prefix o: <https://example.org/space#> .
    @prefix owl: <http://www.w3.org/2002/07/owl#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
    @prefix kv: <https://w3id.org/knowledge-store/values#> .
    <https://example.org/space> a owl:Ontology .
    o:liftoff a owl:DatatypeProperty ; rdfs:range xsd:dateTime .
    o:cruise a owl:DatatypeProperty ; rdfs:range xsd:duration .
    o:window a owl:DatatypeProperty ; rdfs:range kv:interval .
    o:cost a owl:DatatypeProperty ; rdfs:range xsd:decimal ;
        kv:unit <http://qudt.org/vocab/unit/USD> .
    """
    loaded = model.load(data=ttl)
    assert loaded.attributes["liftoff"].range == ("dateTime",)
    assert loaded.attributes["cruise"].range == ("duration",)
    assert loaded.attributes["window"].range == ("interval",)
    assert loaded.attributes["cost"].range == ("decimal",)
    assert loaded.attributes["cost"].unit == "http://qudt.org/vocab/unit/USD"
    assert "decimal http://qudt.org/vocab/unit/USD" in loaded.vocabulary_prompt()


def test_a_name_used_by_a_class_and_a_property_is_refused():
    bad = TTL + "\no:Mission a owl:DatatypeProperty .\n"
    with pytest.raises(ValueError, match="unique"):
        model.load(data=bad)


def test_the_namespace_without_an_ontology_header_is_the_one_most_classes_share():
    ttl = """@prefix owl: <http://www.w3.org/2002/07/owl#> .
    <https://a.org/v/A> a owl:Class . <https://a.org/v/B> a owl:Class . <https://b.org#C> a owl:Class ."""
    s = model.load(data=ttl)
    assert s.namespace == "https://a.org/v/" and set(s.classes) == {"A", "B"} and s.version == ""


def test_an_ontology_iri_ending_in_a_slash_is_its_namespace():
    ttl = """@prefix owl: <http://www.w3.org/2002/07/owl#> .
    <https://a.org/v/> a owl:Ontology . <https://a.org/v/A> a owl:Class ."""
    assert model.load(data=ttl).namespace == "https://a.org/v/"


def test_an_empty_graph_has_no_namespace_and_is_empty():
    s = model.load(data="")
    assert s.namespace == "" and s.is_empty()


def test_load_reads_a_file(tmp_path):
    p = tmp_path / "o.ttl"
    p.write_text(TTL)
    assert "Mission" in model.load(p).classes


def test_empty_spec_has_a_version_and_no_classes():
    e = model.empty()
    assert e.version == "0.0.0" and e.is_empty() and e.namespace.endswith("#")


def test_ancestors_include_the_class_and_its_parents(s):
    assert s.ancestors("SpaceAgency") == {"SpaceAgency", "Organisation"}
    assert s.ancestors("Unknown") == set()


def test_is_a_follows_the_hierarchy(s):
    assert s.is_a("CrewedMission", "Mission") and not s.is_a("Mission", "CrewedMission")


def test_root_is_the_top_of_the_parent_chain(s):
    assert s.root("CrewedMission") == "Mission" and s.root("Mission") == "Mission" and s.root("Nope") == "Nope"


def test_root_stops_on_a_cycle():
    ttl = """@prefix o: <https://c.org#> . @prefix owl: <http://www.w3.org/2002/07/owl#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    <https://c.org> a owl:Ontology . o:A a owl:Class ; rdfs:subClassOf o:B . o:B a owl:Class ; rdfs:subClassOf o:A ."""
    s = model.load(data=ttl)
    assert s.root("A") in {"A", "B"}
    assert s.ancestors("A") == {"A", "B"}


def test_allows_checks_domain_and_range_through_subclasses(s):
    r = s.relations["launchedBy"]
    assert s.allows(r, "CrewedMission", "SpaceAgency")
    assert not s.allows(r, "Target", "SpaceAgency")
    assert not s.allows(r, "Mission", "Target")
    assert s.allows(r, "Mission")


def test_an_attribute_without_a_domain_is_allowed_anywhere(s):
    assert s.allows(s.attributes["motto"], "Target", "anything")


def test_term_finds_classes_relations_and_attributes(s):
    assert s.term("Mission").local == "Mission"
    assert s.term("studies").kind == "relation"
    assert s.term("budget").kind == "attribute"
    assert s.term("nothing") is None


def test_iri_of_an_unknown_term_is_in_the_namespace(s):
    assert str(s.iri_of("Mission")) == "https://example.org/space#Mission"
    assert str(s.iri_of("New")) == "https://example.org/space#New"


def test_the_synonym_index_finds_a_term_by_label_local_name_or_synonym(s):
    idx = s.synonym_index
    assert idx["space agency"] == idx["agency"] == idx[model.normalise("SpaceAgency")] == "SpaceAgency"
    assert idx["launched by"] == "launchedBy"


@pytest.mark.parametrize("raw,key", [("SpaceAgency", "space agency"), ("launch_year", "launch year"), ("  Mission!! ", "mission"), ("R2D2", "r2 d2")])
def test_normalise_folds_case_spacing_punctuation_and_camel_case(raw, key):
    assert model.normalise(raw) == key


def test_the_vocabulary_prompt_lists_every_term_with_its_signature(s):
    p = s.vocabulary_prompt()
    assert "- SpaceAgency [a kind of Organisation]: Space agency (also: agency): A body that runs space programmes." in p
    assert "- launchedBy [Mission -> Organisation]: launched by" in p
    assert "- launchYear [Mission: integer]" in p
    assert "- motto [any: string]" in p


def test_a_delta_prompt_keeps_the_focus_terms_and_the_classes_they_reference(s):
    p = s.vocabulary_prompt(only={"studies"})
    assert "studies" in p and "- Mission" in p and "- Target" in p
    assert "launchedBy" not in p and "Organisation" not in p and "## Attributes" not in p


def test_a_term_names_its_label_local_name_and_synonyms(s):
    assert s.classes["SpaceAgency"].names() == ("Space agency", "SpaceAgency", "agency")
