"""The conformer's edge branches: holds, overlaps with an earlier claim, and forms it refuses."""

from knowledge_store.ingestion.domain.chunk import _heading_block, _keep_heading
from knowledge_store.ingestion.domain.conform import conform
from knowledge_store.ingestion.domain.conform.clocks import _zone
from knowledge_store.ingestion.domain.conform.dates import _intervals, _month_at, _point_at, _shared_days
from knowledge_store.ingestion.domain.conform.identifiers import _canon_url, _identifiers
from knowledge_store.ingestion.domain.conform.log import _assemble
from knowledge_store.ingestion.domain.conform.periods import _iso_duration
from knowledge_store.ingestion.domain.delimited import table_text
from knowledge_store.ingestion.domain.sections import sections
from knowledge_store.ingestion.domain.steps import _join


def _text(source: str) -> str:
    return conform(source).text


def _rules(source: str) -> dict[str, dict]:
    return {row["rule"]: row for row in conform(source).rules}


# --- punctuation and folding ------------------------------------------------------------------

def test_a_unicode_line_separator_is_a_newline():
    assert _text("one two three") == "one\ntwo\nthree"
    assert _rules("one two")["newline"]["applied"] == 1


# --- identifiers ------------------------------------------------------------------------------

def test_a_link_in_parentheses_keeps_the_closing_parenthesis_outside():
    assert _text("(see http://Example.com/a).") == "(see http://example.com/a)."


def test_a_link_claimed_earlier_is_not_claimed_again():
    found = [(0, 18, "http://a.example/b", "http://a.example/b", "link")]
    _identifiers("http://A.example/b http://C.example", found)
    assert [item[2] for item in found] == ["http://a.example/b", "http://C.example"]


def test_an_email_or_uuid_inside_a_link_belongs_to_the_link():
    source = "http://x.example/?e=Bob@Example.COM&id=550E8400-E29B-41D4-A716-446655440000"
    assert _text(source) == source.replace("http://x.example", "http://x.example")
    assert "email" not in _rules(source) and "uuid" not in _rules(source)


def test_a_lowercase_email_and_uuid_are_held_as_they_are():
    source = "mail bob@example.com about 550e8400-e29b-41d4-a716-446655440000."
    assert _text(source) == source and conform(source).rules == ()


def test_a_uuid_with_one_brace_is_lowered_whole():
    assert _text("id {550E8400-E29B-41D4-A716-446655440000 here") == "id {550e8400-e29b-41d4-a716-446655440000 here"


def test_a_link_with_no_host_or_a_bad_port_stays():
    for source in ("see http:///path now", "see http://Host:99999/x now"):
        assert _text(source) == source
    assert _canon_url("http://[::1") is None


def test_a_link_keeps_a_port_that_is_not_the_default_and_its_user():
    assert _text("at http://Host:8080/x") == "at http://host:8080/x"
    assert _text("at http://Host:80/x") == "at http://host/x"
    assert _text("at http://User:pw@Host/x") == "at http://User:pw@host/x"
    assert _canon_url("HTTP://[::1]:8080/x") == "http://[::1]:8080/x"


# --- clocks -----------------------------------------------------------------------------------

def test_a_clock_that_cannot_be_read_stays():
    for source in ("at 13:00 PM", "at 10:30 +25:00", "at 10:30 -2500", "Sent at 15:22:00-07:00."):
        assert _text(source) == source
    assert _zone("+5") is None


def test_a_zone_written_once_on_a_range_applies_to_both_ends():
    assert _text("from 09:15 UTC to 17:30") == "from 09:15Z/17:30Z"
    assert _text("On 2026-03-12 09:15 UTC - 09:35.") == "On 2026-03-12T09:15Z/2026-03-12T09:35Z."


# --- dates ------------------------------------------------------------------------------------

def test_a_date_with_an_unreadable_clock_or_day_stays():
    assert _text("On 14 July 2023 at 25:30.") == "On 2023-07-14 at 25:30."
    assert _text("from 14 July 2023 to 31 February 2023") == "from 2023-07-14 to 31 February 2023"
    for source in ("from 2023-07-14 - 2023-07-32", "Window 2023-02-30 to 2023-03-01.",
                   "on 30-31 February 2023.", "on 32 July 2023."):
        assert _text(source) == source, source
    assert _text("Noted in July. 2023.") == "Noted in July. 2023."


def test_a_shared_month_claimed_earlier_is_not_claimed_again():
    found = [(0, 17, "15-16 July 2023", "15-16 July 2023", "hold")]
    _shared_days("15-16 July 2023", found)
    assert len(found) == 1


def test_an_interval_prefix_claimed_earlier_is_left_out_of_the_span():
    text = "from 2023-07-14 to 2023-07-20"
    found = [(0, 4, "from", "from", "hold")]
    _intervals(text, found, [5], _point_at)
    assert found[-1][2:4] == ("2023-07-14 to 2023-07-20", "2023-07-14/2023-07-20")


def test_a_month_is_only_read_where_the_month_pattern_matched():
    assert _month_at("nothing here", 0) is None


# --- periods ----------------------------------------------------------------------------------

def test_seconds_and_milliseconds_add_up():
    assert _text("wait 30 seconds and 500 ms") == "wait PT30.5S"


def test_a_duration_inside_a_link_belongs_to_the_link():
    for source in ("see http://x.example/2-3days now", "see http://x.example/2days now"):
        assert _text(source) == source
        assert "period" not in _rules(source)


def test_a_duration_that_is_not_one_is_refused():
    assert _iso_duration([("1", "fortnight")]) is None
    assert _iso_duration([("2", "hours"), ("3", "hours")]) is None
    assert _iso_duration([("2", "hours"), ("3", "days")]) is None
    assert _iso_duration([]) is None


# --- sizes ------------------------------------------------------------------------------------

def test_a_size_inside_a_link_belongs_to_the_link():
    for source in ("see http://x.example/1-2MB now", "see http://x.example/8MB now"):
        assert _text(source) == source
        assert "size" not in _rules(source)


def test_a_bare_b_range_stays():
    assert _text("pages 100-200B") == "pages 100-200B"


# --- numbers ----------------------------------------------------------------------------------

def test_a_scientific_number_inside_a_link_or_out_of_range_stays():
    for source in ("see http://x.example/1.5e3 now", "about 1e99 and 1e-19"):
        assert _text(source) == source


def test_a_minus_sign_is_folded_by_the_punctuation_rule():
    assert _text("Down −5.") == "Down -5."
    assert "number" not in _rules("Down −5.")


# --- the claim log ----------------------------------------------------------------------------

def test_an_overlapping_claim_is_dropped_at_assembly():
    body, kept = _assemble("abcdef", [(0, 3, "abc", "X", "r"), (1, 4, "bcd", "Y", "r")])
    assert body == "Xdef" and [k[3] for k in kept] == ["X"]


# --- rows, sections and pages -----------------------------------------------------------------

def test_an_empty_extra_cell_adds_no_column():
    text, _ = table_text("a,b\n1,2,,3\n", tab=False)
    assert text == "a: 1 | b: 2 | column 3: 3"


def test_no_text_has_no_sections():
    assert sections("", headings=True) == []


def test_blank_parts_are_left_out_of_the_joined_document():
    assert _join(["", "  ", "a"]) == ("a", [(0, 1)])


def test_a_heading_that_leaves_no_room_stays_its_own_passage():
    heading = "# " + "x" * 98
    text = heading + "\n\n" + "body " * 40
    blocks = [(0, len(heading)), (len(heading) + 2, len(text))]
    assert _keep_heading(text, blocks, 100) == blocks
    assert _heading_block("  \n ") is False


def test_a_section_that_does_not_start_with_a_heading_keeps_its_blocks():
    blocks = [(0, 5), (7, 11)]
    assert _keep_heading("plain\n\nmore", blocks, 100) == blocks
    assert _heading_block("Title\n=====") is True and _heading_block("plain") is False
