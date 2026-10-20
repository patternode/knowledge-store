"""ontology.domain.renditions: every consumer's form, a pure function of the master."""

import json

import pytest
from rdflib import Graph

from knowledge_store.ontology.domain import renditions
from knowledge_store.ontology.domain.mapping import Column, Mapping, Metric, Table
from ks_ontology_sample import TTL, spec

SHAPES = b"@prefix sh: <http://www.w3.org/ns/shacl#> .\n"


@pytest.fixture(scope="module")
def s():
    return spec()


def _mapping():
    missions = Table(name="missions", location="tables/missions.csv", logical_table="missions", class_name="Mission", key=("id",),
                     columns=(Column(name="year", attribute="launchYear", datatype="integer"), Column(name="agency", relation="launchedBy", range="Organisation", match="code")))
    orgs = Table(name="orgs", location="tables/orgs.csv", logical_table="orgs", class_name="Organisation", key=("code",), columns=())
    return Mapping((missions, orgs), (Metric(name="count", description="How many", expression="SELECT 1", source_table="missions"),))


def test_rel_type_is_upper_snake_case():
    assert renditions.rel_type("launchedBy") == "LAUNCHED_BY" and renditions.rel_type("studies") == "STUDIES"


def test_label_of_capitalises_the_first_letter():
    assert renditions.label_of("spaceAgency") == "SpaceAgency" and renditions.label_of("") == ""


def test_a_reserved_attribute_name_is_stored_with_a_prefix():
    assert renditions.property_of("name") == "a_name" and renditions.property_of("budget") == "budget"


def test_read_master_reads_ontology_and_shapes(tmp_path):
    (tmp_path / "ontology.ttl").write_text(TTL)
    s, ttl, shapes = renditions.read_master(tmp_path)
    assert "Mission" in s.classes and ttl.startswith(b"\n@prefix") and shapes is None
    (tmp_path / "shapes.ttl").write_bytes(SHAPES)
    assert renditions.read_master(tmp_path)[2] == SHAPES


def test_read_master_without_an_ontology_is_refused(tmp_path):
    with pytest.raises(ValueError, match="no master ontology"):
        renditions.read_master(tmp_path)


def test_render_all_writes_every_rendition(s):
    files = renditions.render_all(s, TTL.encode(), SHAPES)
    assert set(files) == {"owl/ontology.ttl", "owl/shapes.ttl", "agent/ontology.md", "agent/ontology.json", "neo4j/schema.cypher",
                          "neo4j/mapping.json", "neo4j/schema.md", "age/schema.sql", "extraction/tool.json", "jsonld/context.jsonld"}
    assert files["owl/ontology.ttl"] == TTL.encode()


def test_renditions_are_deterministic(s):
    assert renditions.render_all(s, TTL.encode(), None) == renditions.render_all(spec(), TTL.encode(), None)


def test_shapes_that_do_not_parse_are_refused(s):
    with pytest.raises(Exception):
        renditions.render_all(s, TTL.encode(), b"this is not turtle {")


def test_a_mapping_adds_its_renditions_and_agent_lines(s):
    files = renditions.render_all(s, TTL.encode(), None, _mapping())
    assert json.loads(files["structured/mapping.json"])["tables"][0]["class"] == "Mission"
    Graph().parse(data=files["r2rml/mapping.ttl"].decode(), format="turtle")
    md = files["agent/ontology.md"].decode()
    assert "## Mapped tables" in md and "metric count over `missions`" in md


def test_the_agent_markdown_nests_types_under_their_parents(s):
    md = renditions.render_all(s, TTL.encode(), None)["agent/ontology.md"].decode()
    assert md.startswith("# Space 1.2.0")
    assert "- Organisation: Organisation\n  - SpaceAgency: A body that runs space programmes. (also: agency)" in md
    assert "- launchedBy: Mission -> Organisation." in md and "- motto (string) of any." in md


def test_the_agent_json_lists_types_relations_and_attributes(s):
    j = json.loads(renditions.render_all(s, TTL.encode(), None)["agent/ontology.json"])
    assert [t["name"] for t in j["types"]][:2] == ["CrewedMission", "Mission"]
    assert j["attributes"][1] == {"name": "launchYear", "label": "launchYear", "definition": "", "synonyms": [], "domain": ["Mission"], "datatype": "integer"}


def test_the_neo4j_mapping_gives_labels_with_ancestors_and_relationship_types(s):
    m = json.loads(renditions.render_all(s, TTL.encode(), None)["neo4j/mapping.json"])
    assert m["labels"]["SpaceAgency"]["also"] == ["Organisation"]
    assert m["relationships"]["launchedBy"]["type"] == "LAUNCHED_BY"
    assert "name" in m["reserved"]


def test_the_cypher_schema_indexes_each_class_and_attribute(s):
    c = renditions.render_schema(s, "neo4j/schema.cypher")
    assert "FOR (n:SpaceAgency) ON (n.name)" in c and "mission_launchyear" in c


def test_the_cypher_schema_refuses_a_name_that_is_not_an_identifier(s):
    import dataclasses

    bad = dataclasses.replace(s, classes={**s.classes, "x y": s.classes["Mission"].__class__(iri="i", local="x y", label="x")})
    with pytest.raises(ValueError):
        renditions.render_schema(bad, "neo4j/schema.cypher")


def test_the_age_schema_makes_an_edge_label_per_relation(s):
    sql = renditions.render_schema(s, "age/schema.sql")
    assert "create_elabel('{graph}', 'LAUNCHED_BY')" in sql and "create_elabel('{graph}', 'STUDIES')" in sql


def test_the_graph_schema_markdown_draws_relationships(s):
    md = renditions.render_all(s, TTL.encode(), None)["neo4j/schema.md"].decode()
    assert "- (:Mission)-[:LAUNCHED_BY]->(:Organisation)" in md
    assert "- :SpaceAgency (also :Organisation) {motto}" in md


def test_the_jsonld_context_types_non_string_attributes(s):
    ctx = json.loads(renditions.render_all(s, TTL.encode(), None)["jsonld/context.jsonld"])["@context"]
    assert ctx["launchedBy"]["@type"] == "@id"
    assert ctx["launchYear"]["@type"].endswith("#integer") and "@type" not in ctx["motto"]


def test_checksums_are_sha256_per_file_in_key_order():
    c = renditions.checksums({"b": b"", "a": b"x"})
    assert list(c) == ["a", "b"] and c["b"].startswith("e3b0c442")


def test_write_local_writes_each_file(tmp_path):
    paths = renditions.write_local({"a/b.txt": b"1"}, tmp_path)
    assert paths == [tmp_path / "a/b.txt"] and paths[0].read_bytes() == b"1"
