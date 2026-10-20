"""What Extraction, Ontology and the Knowledge graph rely on from Ingestion's contract: the silver
documents, their passages, and the bronze objects."""

from __future__ import annotations

import pytest

from contract_support import published
from knowledge_store import ingestion

USES = {
    "extraction": ["Passage", "bronze_objects", "load_doc", "load_passages", "silver_doc_ids"],
    "knowledge_graph": ["load_doc", "load_passages", "silver_doc_ids"],
    "ontology": ["load_doc", "load_passages", "silver_doc_ids"],
}


@pytest.mark.parametrize("consumer", sorted(USES))
def test_each_consumer_finds_what_it_uses(consumer):
    published("ingestion", USES[consumer])


def test_every_silver_document_loads_with_its_passages(swept):
    ids = ingestion.silver_doc_ids(swept)
    assert ids
    for doc_id in ids:
        doc = ingestion.load_doc(swept, doc_id)
        passages = ingestion.load_passages(swept, doc_id)
        assert doc["doc_id"] == doc_id and passages
        assert all(isinstance(p, ingestion.Passage) and p.doc_id == doc_id for p in passages)
        assert [p.seq for p in passages] == sorted(p.seq for p in passages)


def test_a_passage_round_trips_through_a_dict():
    p = ingestion.Passage("p1", "d1", 0, 0, 5, "h", "hello")
    assert ingestion.Passage.from_dict(p.to_dict()) == p


def test_bronze_objects_name_where_their_content_is(swept):
    objs = ingestion.bronze_objects(swept)
    assert objs and all(m["doc_id"] == d and m["content_key"].rsplit("/", 1)[1].startswith("content") for d, m in objs.items())


def test_an_empty_lake_has_no_documents(tmp_path):
    from knowledge_store.platform_services import store_from_uri
    lake = store_from_uri(str(tmp_path))
    assert ingestion.silver_doc_ids(lake) == [] and ingestion.bronze_objects(lake) == {}
