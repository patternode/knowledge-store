"""Ingestion domain: format parsers."""

import json

import pytest

from knowledge_store.ingestion.domain import parsers
from knowledge_store.ingestion.domain.parsers import (
    MAX_BYTES, UnsupportedFormat, parse, parse_html, parse_json, parse_markdown, parse_pdf, parse_text,
)


def test_text_takes_its_first_non_blank_line_as_title():
    r = parse_text(b"\n\n  Quarterly notes \nbody")
    assert r.title == "Quarterly notes" and r.parser == "text@1"


def test_text_normalises_windows_line_endings():
    assert parse_text(b"a\r\nb").text == "a\nb"


def test_text_with_a_byte_order_mark_decodes_without_it():
    assert parse_text("﻿hello".encode("utf-8")).text == "hello"


def test_text_in_utf16_decodes():
    assert parse_text("héllo".encode("utf-16")).text == "héllo"


def test_undecodable_bytes_fall_back_to_latin1():
    assert parse_text(b"\xfdabc\xe9").text.endswith("é")


def test_an_empty_text_has_no_title():
    assert parse_text(b"").title is None


def test_a_title_is_capped_at_200_characters():
    assert len(parse_text(b"x" * 500).title) == 200


def test_a_csv_row_carries_its_column_names_and_a_quoted_newline_stays_in_the_cell():
    raw = b'title,note\nmemo,"line one\nline two, still"\n\n,\n'
    r = parse(raw, ".csv")
    assert r.parser == "table@1"
    assert r.text == "title: memo | note: line one line two, still"
    assert r.title == "memo"


def test_a_tsv_uses_tabs_and_a_repeated_header_is_numbered():
    r = parse(b"name\tname\nAda\tLovelace\n", ".tsv")
    assert r.text == "name: Ada | name (2): Lovelace"
    assert r.title == "Ada"


def test_markdown_takes_its_first_heading_as_title():
    r = parse_markdown(b"intro\n# The Heading \nbody")
    assert r.title == "The Heading" and r.parser == "markdown@1"


def test_markdown_without_a_heading_uses_its_first_line():
    assert parse_markdown(b"## sub\nbody").title == "sub"


def test_html_uses_its_title_tag():
    r = parse_html(b"<title>Page</title><p>Body text</p>")
    assert r.title == "Page" and r.text == "Body text" and r.parser == "html@1"


def test_html_without_a_title_uses_its_first_line():
    assert parse_html(b"<p>First</p><p>Second</p>").title == "First"


def test_json_puts_each_string_on_a_labelled_line():
    r = parse_json(json.dumps({"title": "T", "a": {"b": [1, "x", None, " "]}}).encode())
    assert r.text.splitlines() == ["title: T", "a.b[0]: 1", "a.b[1]: x"]
    assert r.title == "T" and r.parser == "json@1"


def test_json_falls_back_to_name_for_the_title():
    assert parse_json(b'{"name": "N"}').title == "N"


def test_a_json_list_has_no_title():
    r = parse_json(b'["a", "b"]')
    assert r.title is None and r.text == "[0]: a\n[1]: b"


def test_malformed_json_raises():
    with pytest.raises(json.JSONDecodeError):
        parse_json(b"{not json")


def test_parse_chooses_by_extension_case_insensitively():
    assert parse(b"# H\nx", ".MD").parser == "markdown@1"


def test_parse_falls_back_to_the_content_type():
    assert parse(b"<p>x</p>", ".bin", "text/html; charset=utf-8").parser == "html@1"


def test_parse_refuses_an_unknown_format():
    with pytest.raises(UnsupportedFormat, match="no parser for .xyz"):
        parse(b"x", ".xyz")


def test_parse_names_the_content_type_when_there_is_no_extension():
    with pytest.raises(UnsupportedFormat, match="image/png"):
        parse(b"x", "", "image/png")


def test_parse_refuses_an_input_over_the_size_limit(monkeypatch):
    monkeypatch.setattr(parsers, "MAX_BYTES", 10)
    with pytest.raises(UnsupportedFormat, match="over the"):
        parse(b"x" * 11, ".txt")


def test_pdf_has_a_larger_size_limit_than_other_formats():
    assert parsers.MAX_BYTES_BY_PARSER[parse_pdf] > MAX_BYTES


def test_pdf_without_pypdf_is_unsupported(monkeypatch):
    import builtins
    real = builtins.__import__

    def no_pypdf(name, *a, **k):
        if name == "pypdf":
            raise ImportError("no pypdf")
        return real(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", no_pypdf)
    with pytest.raises(UnsupportedFormat, match="pypdf"):
        parse_pdf(b"%PDF")


def _pdf(text: str | None, title: str | None = None) -> bytes:
    pypdf = pytest.importorskip("pypdf")
    import io
    w = pypdf.PdfWriter()
    w.add_blank_page(width=200, height=200)
    if title:
        w.add_metadata({"/Title": title})
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def test_a_pdf_with_no_text_layer_is_unsupported():
    with pytest.raises(UnsupportedFormat, match="no text layer"):
        parse_pdf(_pdf(None))


def test_a_pdf_with_text_returns_its_pages(monkeypatch):
    pypdf = pytest.importorskip("pypdf")
    monkeypatch.setattr(pypdf.PageObject, "extract_text", lambda self, *a, **k: "Page text\nmore")
    r = parse_pdf(_pdf(None, title="Doc Title"))
    assert r.text == "Page text\nmore" and r.title == "Doc Title"
    assert r.parser == "pdf@1" and r.metadata == {"pages": 1}
    assert r.parts == ("Page text\nmore",)
