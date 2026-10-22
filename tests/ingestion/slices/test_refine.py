"""Ingestion slice: refine bronze into silver documents and passages, over a local lake."""

from __future__ import annotations

import json

import pytest

from knowledge_store.ingestion.slices.ingest import ingest
from knowledge_store.ingestion.slices.refine import (
    MIN_TEXT_CHARS, load_doc, load_passages, refine_all, refine_one, silver_doc_ids,
)
from knowledge_store.platform_services import SourceConfig, layout
from knowledge_store.platform_services.adapters.store import LocalStore
from test_ingest import FakeSource

PROSE = b"# Annual review\n\n" + (b"The company grew its revenue in every region this year. " * 3).rstrip()


@pytest.fixture
def lake(tmp_path):
    return LocalStore(tmp_path)


def _ingest(lake, files: dict[str, bytes], content_type: str | None = "text/plain"):
    ingest(lake, SourceConfig("docs", "fake", scope="private"),
           FakeSource({k: ("1", v) for k, v in files.items()}, content_type))
    return {k: layout.sha256(v) for k, v in files.items()}


def test_a_document_is_refined_into_silver_with_its_passages(lake):
    ids = _ingest(lake, {"review.md": PROSE})
    rows = refine_all(lake)
    doc_id = ids["review.md"]
    assert rows == [{"doc_id": doc_id, "status": "refined", "passages": 1}]
    doc = load_doc(lake, doc_id)
    assert doc["title"] == "Annual review" and doc["parser"] == "markdown@1" and doc["scope"] == "private"
    assert doc["chunker"] == "chunk@1" and doc["conformer"] == "conform@1" and doc["passages"] == 1
    assert "conform" not in doc["metadata"]
    assert [p.doc_id for p in load_passages(lake, doc_id)] == [doc_id]
    assert silver_doc_ids(lake) == [doc_id]


def test_a_refined_document_is_not_refined_again(lake):
    _ingest(lake, {"review.md": PROSE})
    refine_all(lake)
    assert refine_all(lake) == []


def test_reparse_refines_again(lake):
    _ingest(lake, {"review.md": PROSE})
    refine_all(lake)
    assert [r["status"] for r in refine_all(lake, reparse=True)] == ["refined"]


def test_an_unsupported_format_is_recorded_as_skipped(lake):
    ids = _ingest(lake, {"pic.xyz": b"\x00\x01"}, content_type=None)
    rows = refine_all(lake)
    assert rows[0]["status"] == "unsupported"
    assert json.loads(lake.get(layout.skipped_key(ids["pic.xyz"])))["status"] == "unsupported"
    assert refine_all(lake) == []


def test_a_malformed_file_is_recorded_not_fatal(lake):
    _ingest(lake, {"bad.json": b"{not json"})
    assert refine_all(lake)[0]["status"] == "parse_failed"


def test_a_near_empty_document_is_skipped(lake):
    _ingest(lake, {"tiny.txt": b"x" * (MIN_TEXT_CHARS - 1)})
    row = refine_all(lake)[0]
    assert row["status"] == "empty" and str(MIN_TEXT_CHARS) in row["reason"]


def test_a_mapped_file_is_skipped_once_as_a_table(lake):
    ids = _ingest(lake, {"table.csv": b"a,b\n1,2\n" * 20})
    rows = refine_all(lake, mapped=[ids["table.csv"]])
    assert rows[0]["status"] == "mapped"
    assert refine_all(lake, mapped=[ids["table.csv"]]) == []
    assert silver_doc_ids(lake) == []


def test_the_limit_caps_the_rows(lake):
    _ingest(lake, {f"{i}.md": PROSE + str(i).encode() for i in range(3)})
    assert len(refine_all(lake, limit=2)) == 2


def test_a_document_without_a_title_uses_its_file_name(lake):
    ids = _ingest(lake, {"data.json": json.dumps({"body": "x" * 60}).encode()})
    refine_all(lake)
    assert load_doc(lake, ids["data.json"])["title"] == "data.json"


def test_refine_one_merges_parser_metadata_into_the_source_metadata(lake):
    ids = _ingest(lake, {"review.md": PROSE})
    meta = {"doc_id": ids["review.md"], "content_key": layout.bronze_content_key("docs", ids["review.md"], ".md"),
            "ext": ".md", "source": "docs", "metadata": {"folder": "x"}}
    assert refine_one(lake, meta)["status"] == "refined"
    doc = load_doc(lake, ids["review.md"])
    assert doc["metadata"] == {"folder": "x"} and doc["scope"] == "public"


def test_an_unknown_extension_is_parsed_by_its_content_type(lake):
    _ingest(lake, {"notes.xyz": PROSE}, content_type="text/plain")
    assert refine_all(lake)[0]["status"] == "refined"


def test_refine_conforms_the_text_and_the_title_and_records_the_rules(lake):
    body = (
        "# Review of 14 July 2023\n\n"
        "Revenue was $1,200.50 on 13/01/2024 at 3:30 PM, up 12 percent. "
        "The other date stayed 01/02/2024 and the call was at 3:30.\n"
    )
    ids = _ingest(lake, {"review.md": body.encode()})
    assert refine_all(lake)[0]["status"] == "refined"
    doc = load_doc(lake, ids["review.md"])
    assert doc["conformer"] == "conform@1"
    assert doc["title"] == "Review of 2023-07-14"
    assert "$1200.5" in doc["text"] and "2024-01-13T15:30" in doc["text"] and "12%" in doc["text"]
    assert "01/02/2024" in doc["text"] and "3:30" in doc["text"]
    rules = {row["rule"]: row for row in doc["metadata"]["conform"]}
    assert rules["date"]["applied"] >= 1 and rules["number"]["applied"] >= 1
    assert "$1200.5" in load_passages(lake, ids["review.md"])[0].text
