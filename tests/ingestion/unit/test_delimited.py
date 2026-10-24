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
    assert table_text("\n", tab=False) == ("", None)


def test_a_header_only_file_has_no_rows():
    assert table_text("amount,when\n", tab=False) == ("", None)


def test_a_title_column_wins_over_a_name_column_whichever_is_first():
    text, title = table_text("name,title\nAda,The Report\n", tab=False)
    assert text == "name: Ada | title: The Report"
    assert title == "The Report"


def test_a_name_column_is_the_title_when_there_is_no_title_column():
    assert table_text("name,note\nAda,hi\n", tab=False)[1] == "Ada"


def test_a_later_row_does_not_replace_the_title():
    assert table_text("title\nFirst\nSecond\n", tab=False)[1] == "First"


def test_an_empty_title_cell_falls_through_to_the_next_title_not_to_a_name():
    _, title = table_text("name,title\nAda,\nGrace,The Report\n", tab=False)
    assert title == "The Report"


def test_a_second_name_column_supplies_the_title_when_the_first_is_empty():
    text, title = table_text("name,name\n,Lovelace\n", tab=False)
    assert text == "name (2): Lovelace"
    assert title == "Lovelace"


def test_a_title_is_capped_at_200_characters():
    assert len(table_text("title\n" + ("x" * 250) + "\n", tab=False)[1]) == 200


def test_whitespace_inside_a_cell_collapses():
    assert table_text("name\n  Ada \t Lovelace  \n", tab=False)[0] == "name: Ada Lovelace"


def test_a_quoted_quote_stays_inside_the_cell():
    assert table_text('said\n"say ""hi"""\n', tab=False)[0] == 'said: say "hi"'


def test_a_short_row_omits_the_missing_cells():
    assert table_text("a,b,c\n1\n", tab=False)[0] == "a: 1"


def test_windows_and_old_mac_line_endings_are_rows():
    assert table_text("a,b\r\n1,2\r\n", tab=False)[0] == "a: 1 | b: 2"
    assert table_text("a,b\r1,2\r", tab=False)[0] == "a: 1 | b: 2"
    assert table_text('note\r\n"line one\r\nline two"\r\n', tab=False)[0] == "note: line one line two"


def test_a_row_of_empty_cells_is_dropped():
    assert table_text("a,b\n1,2\n,,\n , \n3,4\n", tab=False)[0] == "a: 1 | b: 2\na: 3 | b: 4"


def test_a_blank_header_is_numbered_and_an_extra_cell_does_not_reuse_it():
    text, title = table_text("column 2,\nvalue,extra,more\n", tab=False)
    assert text == "column 2: value | column 3: extra | column 4: more"
    assert title is None


def test_repeated_headers_stay_distinct_when_one_of_them_is_already_numbered():
    text, _ = table_text("name,name (2),name\nA,B,C\n", tab=False)
    assert text == "name: A | name (2): B | name (3): C"


def test_a_cell_that_contains_the_separator_is_written_with_a_slash():
    text, _ = table_text('note,more\n"left | right",tail\n', tab=False)
    assert text == "note: left / right | more: tail"


def test_a_semicolon_stays_inside_a_csv_cell_and_a_comma_stays_inside_a_tab_cell():
    assert table_text("a;b\n1;2\n", tab=False)[0] == "a;b: 1;2"
    assert table_text("note\tmore\nhello, world\tx\n", tab=True)[0] == "note: hello, world | more: x"


def test_spaces_around_a_header_are_not_part_of_its_name():
    text, title = table_text("  Title  , name \nReport,Ada\n", tab=False)
    assert text == "Title: Report | name: Ada"
    assert title == "Report"
