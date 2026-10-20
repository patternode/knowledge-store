"""ontology.slices.versions: publish, activate, diff and classify versions."""

import json

import pytest

from knowledge_store.ontology.domain import model
from knowledge_store.ontology.slices import versions
from knowledge_store.platform_services.adapters.store import LocalStore
from knowledge_store.platform_services.domain import layout
from ks_ontology_lake import bump, master, published
from ks_ontology_sample import TTL


@pytest.fixture
def lake(tmp_path):
    return LocalStore(tmp_path / "lake")


def _spec(ttl=TTL):
    return model.load(data=ttl)


@pytest.mark.parametrize("change,kind", [
    (lambda t: t, "none"),
    (lambda t: t.replace('rdfs:label "Target"@en', 'rdfs:label "Destination"@en'), "descriptive"),
    (lambda t: t.replace('rdfs:label "Space"@en', 'rdfs:label "Space flight"@en'), "descriptive"),
    (lambda t: t + "\no:Rover a owl:Class .\n", "additive"),
    (lambda t: t.replace("o:CrewedMission a owl:Class ; rdfs:subClassOf o:Mission .", "o:CrewedMission a owl:Class ."), "semantic"),
    (lambda t: t.replace("rdfs:range o:Target", "rdfs:range o:Mission"), "semantic"),
    (lambda t: t.replace("o:motto a owl:DatatypeProperty .", ""), "removal"),
    (lambda t: t.replace("o:motto a owl:DatatypeProperty .", "o:motto a owl:ObjectProperty ."), "semantic"),
])
def test_diff_classifies_the_change(change, kind):
    assert versions.diff(_spec(), _spec(change(TTL))).kind == kind


def test_a_removal_outranks_everything_else():
    d = versions.Diff(added=["a"], removed=["b"], semantic=["c"], descriptive=["d"])
    assert d.kind == "removal" and d.to_dict()["kind"] == "removal"


@pytest.mark.parametrize("kind,bump_", [("descriptive", "patch"), ("additive", "minor"), ("semantic", "major"), ("removal", "major"), ("none", "none")])
def test_each_kind_needs_its_bump(kind, bump_):
    assert versions.required_bump(kind) == bump_


@pytest.mark.parametrize("old,new,b", [("1.2.3", "1.2.4", "patch"), ("1.2.3", "1.3.0", "minor"), ("1.2.3", "2.0.0", "major")])
def test_bump_of_names_the_bump(old, new, b):
    assert versions.bump_of(old, new) == b


@pytest.mark.parametrize("old,new", [("1.2", "1.3.0"), ("1.2.3", "1.2.3"), ("1.2.3", "1.1.9")])
def test_bump_of_refuses_non_semver_or_backwards(old, new):
    with pytest.raises(ValueError):
        versions.bump_of(old, new)


def test_a_fresh_lake_has_no_active_version(lake):
    assert versions.active_version(lake) is None and versions.published_versions(lake) == []


def test_the_first_publish_is_initial_renders_and_activates(lake, tmp_path):
    m = published(lake, tmp_path)
    assert m["kind"] == "initial" and m["base"] is None and m["counts"]["classes"] == 5
    assert versions.active_version(lake) == "1.2.0"
    assert lake.exists("ontology/versions/1.2.0/renditions/neo4j/schema.cypher")
    assert versions.manifest(lake, "1.2.0")["sha256"]["ontology.ttl"]
    spec, shapes = versions.load_version(lake, "1.2.0")
    assert "Mission" in spec.classes and shapes is None


def test_publishing_without_activating_leaves_the_active_version(lake, tmp_path):
    published(lake, tmp_path, activate=False)
    assert versions.active_version(lake) is None and versions.published_versions(lake) == ["1.2.0"]


def test_an_additive_version_names_its_base_and_its_delta_and_chains(lake, tmp_path):
    published(lake, tmp_path)
    m = published(lake, tmp_path, bump(TTL, "1.3.0") + "\no:Rover a owl:Class .\n", name="m2")
    assert (m["kind"], m["base"], m["delta_terms"]) == ("additive", "1.2.0", ["Rover"])
    assert versions.chain(lake, "1.3.0") == ["1.3.0", "1.2.0"]
    assert versions.published_versions(lake) == ["1.2.0", "1.3.0"]


def test_force_full_makes_an_additive_version_a_full_one(lake, tmp_path):
    published(lake, tmp_path)
    m = versions.publish(lake, master(tmp_path, bump(TTL, "1.3.0") + "\no:Rover a owl:Class .\n", "m2"), force_full=True)
    assert m["kind"] == "semantic" and versions.chain(lake, "1.3.0") == ["1.3.0"]


def test_an_under_bumped_version_is_refused(lake, tmp_path):
    published(lake, tmp_path)
    with pytest.raises(ValueError, match="needs a minor bump"):
        published(lake, tmp_path, bump(TTL, "1.2.1") + "\no:Rover a owl:Class .\n", name="m2")


def test_a_version_identical_to_the_active_one_is_refused(lake, tmp_path):
    published(lake, tmp_path)
    with pytest.raises(ValueError, match="identical"):
        published(lake, tmp_path, bump(TTL, "1.2.1"), name="m2")


def test_a_published_version_is_immutable(lake, tmp_path):
    published(lake, tmp_path)
    with pytest.raises(ValueError, match="immutable"):
        published(lake, tmp_path, name="m2")


def test_a_version_that_is_not_semver_is_refused(lake, tmp_path):
    with pytest.raises(ValueError, match="semver"):
        published(lake, tmp_path, TTL.replace('owl:versionInfo "1.2.0"', 'owl:versionInfo "v1"'))


def test_an_ontology_without_classes_is_refused(lake, tmp_path):
    ttl = '@prefix owl: <http://www.w3.org/2002/07/owl#> .\n<https://e.org/o> a owl:Ontology ; owl:versionInfo "1.0.0" .\n'
    with pytest.raises(ValueError, match="no classes"):
        published(lake, tmp_path, ttl)


def test_a_version_iri_that_names_another_version_is_refused(lake, tmp_path):
    with pytest.raises(ValueError, match="versionIRI"):
        published(lake, tmp_path, TTL.replace("/1.2.0>", "/9.9.9>"))


def test_shapes_and_a_mapping_are_published_with_the_version(lake, tmp_path):
    d = master(tmp_path)
    (d / "shapes.ttl").write_text("@prefix sh: <http://www.w3.org/ns/shacl#> .\n")
    (d / "mappings.yaml").write_text("tables:\n  missions:\n    location: tables/m.csv\n    class: Mission\n    key: id\n    columns:\n      year: {attribute: launchYear}\n")
    m = versions.publish(lake, d, activate=True)
    assert set(m["sha256"]) == {"ontology.ttl", "shapes.ttl", "mappings.yaml"}
    assert m["changes"]["mapping"] == ["table missions"]
    assert versions.load_version(lake, "1.2.0")[1] is not None
    assert versions._published_mapping(lake, "1.2.0").table("missions").class_name == "Mission"


def test_a_mapping_only_change_needs_its_own_bump(lake, tmp_path):
    published(lake, tmp_path)
    d = master(tmp_path, bump(TTL, "1.3.0"), "m2")
    (d / "mappings.yaml").write_text("tables:\n  missions:\n    location: tables/m.csv\n    class: Mission\n    key: id\n    columns:\n      year: {attribute: launchYear}\n")
    m = versions.publish(lake, d)
    assert m["kind"] == "additive" and m["changes"]["kind"] == "additive" and m["changes"]["mapping"] == ["table missions"]


def test_activating_a_version_that_was_never_published_fails(lake):
    with pytest.raises(Exception):
        versions.activate_version(lake, "9.9.9")


def test_activation_records_the_version(lake, tmp_path):
    published(lake, tmp_path, activate=False)
    versions.activate_version(lake, "1.2.0")
    assert json.loads(lake.get(layout.ONTOLOGY_ACTIVE))["version"] == "1.2.0"
