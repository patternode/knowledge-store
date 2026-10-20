"""ontology.slices.provided: an ontology a deployer brings, published and activated by the sweep."""

import pytest

from knowledge_store.ontology.slices import provided, versions
from knowledge_store.platform_services.adapters.store import LocalStore
from ks_ontology_lake import bump
from ks_ontology_sample import TTL

MAPPING = b"tables:\n  missions:\n    location: tables/m.csv\n    class: Mission\n    key: id\n    columns:\n      year: {attribute: launchYear}\n"


@pytest.fixture
def lake(tmp_path):
    return LocalStore(tmp_path)


def _provide(lake, ttl=TTL, shapes=None, mapping=None):
    lake.put(provided.ONTOLOGY_KEY, ttl.encode())
    if shapes is not None:
        lake.put(provided.SHAPES_KEY, shapes)
    if mapping is not None:
        lake.put(provided.MAPPING_KEY, mapping)


def test_without_a_provided_ontology_nothing_happens(lake):
    assert not provided.present(lake) and provided.apply(lake) is None


def test_a_new_ontology_is_published_with_generated_shapes_and_activated(lake):
    _provide(lake)
    assert provided.apply(lake) == {"version": "1.2.0", "action": "published", "kind": "initial"}
    assert versions.active_version(lake) == "1.2.0"
    assert versions.manifest(lake, "1.2.0")["note"] == "provided ontology; shapes generated"


def test_provided_shapes_are_used(lake):
    _provide(lake, shapes=b"@prefix sh: <http://www.w3.org/ns/shacl#> .\n")
    provided.apply(lake)
    assert versions.manifest(lake, "1.2.0")["note"] == "provided ontology"


def test_applying_again_is_current(lake):
    _provide(lake)
    provided.apply(lake)
    assert provided.apply(lake)["action"] == "current"


def test_a_published_version_that_is_not_active_is_activated_when_newer(lake):
    _provide(lake)
    provided.apply(lake)
    lake.delete("ontology/active.json")
    assert provided.apply(lake)["action"] == "activated"


def test_an_older_published_version_is_left_inactive(lake):
    _provide(lake)
    provided.apply(lake)
    _provide(lake, bump(TTL, "1.3.0") + "\no:Rover a owl:Class .\n")
    provided.apply(lake)
    _provide(lake)
    assert provided.apply(lake)["action"] == "published, not active"


def test_a_file_that_does_not_parse_is_refused(lake):
    _provide(lake, "not turtle {")
    with pytest.raises(ValueError, match="does not parse"):
        provided.apply(lake)


def test_a_version_that_is_not_semver_is_refused(lake):
    _provide(lake, TTL.replace('owl:versionInfo "1.2.0"', 'owl:versionInfo "latest"'))
    with pytest.raises(ValueError, match="X.Y.Z"):
        provided.apply(lake)


def test_a_changed_file_under_a_published_version_is_refused(lake):
    _provide(lake)
    provided.apply(lake)
    _provide(lake, TTL + "\no:Rover a owl:Class .\n")
    with pytest.raises(ValueError, match="bump the version"):
        provided.apply(lake)


def test_a_mapping_added_under_a_published_version_is_refused(lake):
    _provide(lake)
    provided.apply(lake)
    _provide(lake, mapping=MAPPING)
    with pytest.raises(ValueError, match="mappings.yaml changed"):
        provided.apply(lake)


def test_a_mapping_is_published_with_the_ontology(lake):
    _provide(lake, mapping=MAPPING)
    provided.apply(lake)
    assert "mappings.yaml" in versions.manifest(lake, "1.2.0")["sha256"]


def test_an_older_unpublished_version_is_refused(lake):
    _provide(lake, bump(TTL, "1.3.0"))
    provided.apply(lake)
    _provide(lake, bump(TTL, "1.1.0") + "\no:Rover a owl:Class .\n")
    with pytest.raises(ValueError, match="older than the active"):
        provided.apply(lake)
