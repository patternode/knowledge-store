"""Ingestion domain: HTML to text."""

from knowledge_store.ingestion.domain.html_text import html_title_and_text, html_to_text


def test_a_table_row_becomes_one_line_with_cells_separated():
    text = html_to_text("<table><tr><th>Item</th><td>Revenue</td><td>12</td></tr></table>")
    assert text == "Item | Revenue | 12"


def test_currency_and_percent_cells_glue_to_their_numbers():
    text = html_to_text("<table><tr><td>Margin</td><td>$</td><td>5</td><td>3</td><td>%</td></tr></table>")
    assert text == "Margin | $5 | 3%"


def test_a_parenthesised_negative_stays_one_cell():
    text = html_to_text("<table><tr><td>Loss</td><td>(</td><td>4</td><td>)</td></tr></table>")
    assert text == "Loss | (4)"


def test_empty_cells_and_empty_rows_are_dropped():
    text = html_to_text("<table><tr><td> </td></tr><tr><td>a</td><td></td><td>b</td></tr></table>")
    assert text == "a | b"


def test_scripts_styles_and_the_head_are_skipped():
    raw = "<html><head><style>x{}</style></head><body><script>var a=1</script><p>Visible</p></body></html>"
    assert html_to_text(raw) == "Visible"


def test_block_elements_break_lines():
    assert html_to_text("<p>One</p><p>Two</p>") == "One\n\nTwo"


def test_entities_and_non_breaking_spaces_are_decoded():
    assert html_to_text("<p>A&amp;B&nbsp;C</p>") == "A&B C"


def test_the_title_is_returned_with_whitespace_collapsed():
    title, text = html_title_and_text("<html><head><title>  Annual\n report </title></head><body>Body</body></html>")
    assert title == "Annual report"
    assert text == "Body"


def test_a_missing_or_empty_title_is_none():
    assert html_title_and_text("<p>x</p>")[0] is None
    assert html_title_and_text("<title> </title><p>x</p>")[0] is None


def test_only_the_first_title_counts():
    assert html_title_and_text("<title>One</title><title>Two</title>")[0] == "One"


def test_runs_of_blank_lines_collapse_to_one():
    assert html_to_text("<div><div><div>A</div></div></div><div><div>B</div></div>") == "A\n\nB"


def test_an_unclosed_skip_tag_does_not_go_negative():
    assert html_to_text("</script><p>Still here</p>") == "Still here"
