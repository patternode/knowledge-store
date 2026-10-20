"""platform_services.domain.layout: one place for the lake's object keys."""

from knowledge_store.platform_services.domain import layout


def test_sha256_is_the_hex_digest_of_the_bytes():
    assert layout.sha256(b"") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_bronze_keys_are_partitioned_by_the_first_two_hex_digits():
    d = "ab" + "0" * 62
    assert layout.bronze_prefix("uploads", d) == f"bronze/uploads/ab/{d}"
    assert layout.bronze_content_key("uploads", d, ".pdf") == f"bronze/uploads/ab/{d}/content.pdf"
    assert layout.bronze_meta_key("uploads", d) == f"bronze/uploads/ab/{d}/meta.json"


def test_seen_key_hashes_the_source_key_so_any_text_makes_a_safe_key():
    k = layout.seen_key("web", "https://example.org/a?b=c d")
    assert k.startswith("bronze/_seen/web/") and k.endswith(".json")
    assert len(k.rsplit("/", 1)[1]) == 32 + len(".json")


def test_seen_key_is_stable_for_the_same_source_key():
    assert layout.seen_key("s", "x") == layout.seen_key("s", "x") != layout.seen_key("s", "y")


def test_silver_keys():
    assert layout.doc_key("d1") == "silver/documents/d1.json"
    assert layout.passages_key("d1") == "silver/passages/d1.jsonl"
    assert layout.skipped_key("d1") == "silver/skipped/d1.json"


def test_gold_keys_are_under_the_ontology_version():
    v = "1.2.0"
    assert layout.gold_prefix(v) == "gold/1.2.0"
    assert layout.graph_key(v, "d") == "gold/1.2.0/graph/d.nq"
    assert layout.extraction_key(v, "d") == "gold/1.2.0/extractions/d.json"
    assert layout.rejected_key(v, "d") == "gold/1.2.0/rejected/d.json"
    assert layout.candidates_key(v, "d") == "gold/1.2.0/candidates/d.jsonl"
    assert layout.index_key(v, "classes") == "gold/1.2.0/index/classes.json"


def test_structured_keys_name_the_source_and_snapshot():
    assert layout.structured_binding_key("1") == "gold/1/structured/binding.json"
    assert layout.structured_graph_key("1", "t", "s") == "gold/1/structured/t/s.nq"
    assert layout.structured_cells_key("1", "t", "s") == "gold/1/structured/t/s.jsonl"


def test_ontology_version_prefix():
    assert layout.ontology_version_prefix("0.1.0") == "ontology/versions/0.1.0"


def test_doc_id_from_key_is_the_file_name_without_extension():
    assert layout.doc_id_from_key("silver/passages/abc.jsonl") == "abc"
    assert layout.doc_id_from_key("gold/1.0.0/graph/abc.nq") == "abc"
    assert layout.doc_id_from_key("abc") == "abc"
