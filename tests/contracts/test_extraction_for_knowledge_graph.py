"""What the Knowledge graph relies on from Extraction's contract: the active version, the mapping
it published, the table binding and the data namespace."""

from __future__ import annotations

from contract_support import published
from knowledge_store import extraction, ontology


def test_the_knowledge_graph_finds_what_it_uses():
    published("extraction", ["active", "binding", "data_base", "published_mapping", "mapped_doc_ids"])


def test_the_active_version_is_the_ontologys(swept):
    assert extraction.active(swept) == ontology.versions.active_version(swept)


def test_a_collection_without_a_mapping_binds_nothing(swept):
    assert extraction.published_mapping(swept) is None
    assert extraction.mapped_doc_ids(swept) == set()
    assert isinstance(extraction.binding(swept), dict)


def test_the_data_namespace_comes_from_the_spec(swept):
    spec, _ = ontology.versions.load_version(swept, extraction.active(swept))
    base = extraction.data_base(spec)
    assert isinstance(base, str) and base.startswith("http")
