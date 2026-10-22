"""Ingestion domain: canonical text before any ontology is involved."""

from knowledge_store.ingestion.domain.conform import CONFORMER_VERSION, conform


def _text(source: str) -> str:
    return conform(source).text


def _rules(source: str) -> dict[str, dict]:
    return {row["rule"]: row for row in conform(source).rules}


def test_the_conformer_version_is_recorded():
    assert CONFORMER_VERSION == "conform@1"


def test_a_month_name_date_becomes_iso():
    assert _text("Filed on 14 July 2023.") == "Filed on 2023-07-14."
    assert _text("Filed on July 14, 2023.") == "Filed on 2023-07-14."
    assert _text("Filed on 14th of July, 2023.") == "Filed on 2023-07-14."
    assert _text("Filed on Sept. 3, 2021.") == "Filed on 2021-09-03."
    assert _text("Filed on 3rd of Sept, 2021.") == "Filed on 2021-09-03."
    assert _text("Filed on 14 JULY 2023.") == "Filed on 2023-07-14."


def test_a_numeric_date_is_rewritten_only_when_one_side_is_past_twelve():
    assert _text("Due 13/01/2024.") == "Due 2024-01-13."
    assert _text("Due 01/13/2024.") == "Due 2024-01-13."
    assert _text("Due 13-01-2024.") == "Due 2024-01-13."
    assert "01/02/2024" in _text("Due 01/02/2024.")
    assert "02/31/2024" in _text("Due 02/31/2024.")
    assert "32/01/2024" in _text("Due 32/01/2024.")


def test_a_bare_year_quarter_and_yes_no_stay():
    source = "In 2021 Q3 the answer was yes, then no."
    assert _text(source) == source
    assert conform(source).rules == ()


def test_a_clock_with_a_meridiem_or_a_zone_or_an_hour_past_twelve_is_24_hour():
    assert _text("Call at 3:30 PM.") == "Call at 15:30."
    assert _text("Call at 3:30 p.m.") == "Call at 15:30."
    assert _text("Call at 12:00 AM.") == "Call at 00:00."
    assert _text("Call at 12:00 PM.") == "Call at 12:00."
    assert _text("Call at 3:30:05 PM.") == "Call at 15:30:05."
    assert _text("Call at 15:30 UTC.") == "Call at 15:30Z."
    assert _text("Call at 3:30 pm +0530.") == "Call at 15:30+05:30."
    assert _text("Call at 00:30 UTC.") == "Call at 00:30Z."
    assert _text("Already 15:30.") == "Already 15:30."
    assert _text("Already 15:30:00Z.") == "Already 15:30:00Z."


def test_a_bare_clock_and_a_single_digit_midnight_stay():
    assert _text("Meet at 3:30.") == "Meet at 3:30."
    assert _text("Meet at 0:30.") == "Meet at 0:30."
    assert conform("Meet at 3:30.").rules == ()


def test_a_clock_against_a_date_joins_it():
    assert _text("Met 14 July 2023 at 3:30 PM.") == "Met 2023-07-14T15:30."
    assert _text("Met 14 July 2023, at 3:30 PM.") == "Met 2023-07-14T15:30."
    assert _text("Met 13/01/2024 at 3:30 PM.") == "Met 2024-01-13T15:30."
    assert _text("Met 2023-07-14 15:30 UTC.") == "Met 2023-07-14T15:30Z."
    assert _text("Met 2023-07-14T15:30:00Z.") == "Met 2023-07-14T15:30:00Z."
    assert _text("Met 01/02/2024 at 3:30 PM.") == "Met 01/02/2024 at 15:30."


def test_numbers_use_the_same_canonical_form_as_a_table_cell():
    assert _text("Paid $1,200.50.") == "Paid $1200.5."
    assert _text("Paid €1,200.") == "Paid €1200."
    assert _text("Up 12 percent.") == "Up 12%."
    assert _text("Up 12 per cent.") == "Up 12%."
    assert _text("Up 12 %.") == "Up 12%."
    assert _text("A loss of ($1,200).") == "A loss of -$1200."
    assert _text("A loss of ($1,200.50).") == "A loss of -$1200.5."
    assert _text("Down −1,200.") == "Down -1200."
    assert _text("Down -1,200.") == "Down -1200."
    assert _text("Total 1\u00a0234.") == "Total 1234."
    assert _text("Total 1\u00a0234\u00a0567.") == "Total 1234567."
    assert _text("Kept 12% and 15:30 and 2023-07-14.") == "Kept 12% and 15:30 and 2023-07-14."


def test_a_regular_space_is_not_a_thousands_separator():
    assert _text("Total 1 234 567.") == "Total 1 234 567."
    assert _text("Phone +1 415 555 0199.") == "Phone +1 415 555 0199."
    assert conform("Phone +1 415 555 0199.").rules == ()


def test_parentheses_are_a_loss_only_with_currency_or_a_grouping_separator():
    assert _text("A loss of (1,200).") == "A loss of -1200."
    assert _text("A loss of (1\u00a0234).") == "A loss of -1234."
    assert _text("Next release (1.4).") == "Next release (1.4)."
    assert _text("Python SDK (3.11).") == "Python SDK (3.11)."
    assert _text("Share of payloads (0.5%).") == "Share of payloads (0.5%)."
    assert _text("Driver roll (535.23).") == "Driver roll (535.23)."


def test_plain_integers_versions_lists_and_a_parenthetical_count_stay():
    source = "Version 1.2.3 lists 1, 2 and (5), code 007, range 10-12."
    assert _text(source) == source
    assert _text("Range 1,200-1,500.") == "Range 1200-1500."
    assert _text("See function(1,200) now.") == "See function(1,200) now."
    assert _text("Address 192.168.0.1.") == "Address 192.168.0.1."


def test_structural_folds_do_not_need_a_domain():
    assert _text("opera\u00adting\r\nnext\u00a0word") == "operating\nnext word"
    assert _text("pay \uFF11,\uFF12\uFF10\uFF10 now") == "pay 1200 now"
    source = "line  \n\uFF11,\uFF12\uFF10\uFF10\r\n"
    assert _text(source) == "line\n1200\n"
    assert {"newline", "unicode_digit", "trailing_space", "number"} <= set(_rules(source))


def test_a_combining_mark_is_composed():
    assert _text("cafe\u0301") == "caf\u00e9"
    assert _rules("cafe\u0301")["unicode_form"]["examples"] == ["NFC"]


def test_a_wide_space_that_is_not_a_group_space_folds():
    assert _text("hello\u2003world") == "hello world"
    assert "unicode_space" in _rules("hello\u2003world")


def test_fenced_code_is_not_rewritten():
    source = "Paid $1,200.\n\n```\nPaid $1,200 on 14 July 2023 at 3:30 PM.\n```\n\nDue 13/01/2024."
    text = _text(source)
    assert "Paid $1200." in text
    assert "```\nPaid $1,200 on 14 July 2023 at 3:30 PM.\n```" in text
    assert "Due 2024-01-13." in text


def test_a_clock_range_against_a_date_is_one_span_and_stays():
    source = "During (~2026-03-12 09:15-09:35 UTC) requests moved."
    assert _text(source) == "During (~2026-03-12T09:15-09:35Z) requests moved."
    assert _text("Logged 2026-03-12 09:27 and 2026-03-12 15:20.") == (
        "Logged 2026-03-12T09:27 and 2026-03-12T15:20.")
    once = _text(source)
    assert conform(once).text == once and conform(once).rules == ()


def test_control_characters_and_noncharacters_are_dropped_and_emoji_stays():
    assert _text("a\x07b\x00c\td\n") == "abc\td\n"
    assert _text("a\uffffb\ud800c") == "abc"
    assert _text("ok \U0001f600") == "ok \U0001f600"
    assert "control" in _rules("a\x07b")


def test_a_plain_decimal_loses_trailing_zeros_and_a_version_does_not():
    assert _text("Score 1.20 and build 1.0.") == "Score 1.2 and build 1."
    assert _text("Version 1.2.3.") == "Version 1.2.3."


def test_the_same_text_is_unchanged_the_second_time():
    source = (
        "On 14 July 2023 at 3:30 PM we paid $1,200.50, up 12 percent, "
        "after 13/01/2024 15:30 UTC.\n"
        "Left alone: 01/02/2024, 3:30, 2021, yes, Q3, 1.2.3, (5).\n"
        "```\n$1,200 on 14 July 2023\n```\n"
    )
    once = conform(source)
    twice = conform(once.text)
    assert twice.text == once.text
    assert twice.rules == ()


def test_a_rule_log_keeps_three_examples():
    source = "On 1 May 2020, 2 May 2020, 3 May 2020 and 4 May 2020."
    row = _rules(source)["date"]
    assert row["applied"] == 4
    assert len(row["examples"]) == 3
    assert row["examples"][0] == "1 May 2020 -> 2020-05-01"


def test_an_iso_date_is_not_split_into_numbers():
    source = "Released 2023-07-14T15:30:00Z and offset 2023-07-14T15:30:00+02:00."
    assert _text(source) == source
    assert conform(source).rules == ()
