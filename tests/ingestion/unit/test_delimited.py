"""Ingestion domain: unmapped CSV and TSV rows."""

from knowledge_store.ingestion.domain.delimited import table_text


def test_a_row_keeps_a_quoted_comma_and_a_newline_inside_one_cell():
    text, title = table_text('title,note\nmemo,"line one\nline two, still"\n', tab=False)
    assert text == "title: memo | note: line one line two, still"
    assert title == "memo"


def test_a_blank_row_is_dropped_and_an_extra_cell_is_numbered():
    text, title = table_text("h\n\nvalue,extra\n", tab=False)
    assert text == "h: value | column 2: extra"
    assert title is None


def test_a_tab_file_numbers_a_repeated_header():
    text, title = table_text("name\tname\nAda\tLovelace\n", tab=True)
    assert text == "name: Ada | name (2): Lovelace"
    assert title == "Ada"


def test_an_empty_file_has_no_rows():
    assert table_text("", tab=False) == ("", None)
