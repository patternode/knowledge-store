"""kernel.values: one way to read a literal value and one text form to store it in."""

import datetime as dt
from decimal import Decimal

import pytest

from knowledge_store.kernel.values import canonical, number, parse_value


@pytest.mark.parametrize("text,expected", [("1,100", Decimal("1100")), ("$1,200", Decimal("1200")), ("12.5%", Decimal("12.5")), ("€3", Decimal("3")), (" 7 ", Decimal("7"))])
def test_a_decimal_ignores_thousands_separators_currency_and_percent(text, expected):
    assert parse_value(text, "decimal") == expected


def test_a_decimal_that_is_not_a_number_is_refused():
    with pytest.raises(ValueError, match="not a number"):
        parse_value("about ten", "decimal")


def test_an_integer_ignores_separators_and_currency():
    assert parse_value("£2,000", "integer") == 2000


def test_an_integer_with_a_fraction_is_refused():
    with pytest.raises(ValueError, match="whole number"):
        parse_value("2.5", "integer")


@pytest.mark.parametrize("text", ["2023-07-14", "14 July 2023", "July 14, 2023", "14 Jul 2023", "Jul 14, 2023"])
def test_a_date_is_read_in_any_of_the_written_forms(text):
    assert parse_value(text, "date") == dt.date(2023, 7, 14)


def test_a_bare_year_is_the_first_of_january():
    assert parse_value("2021", "date") == dt.date(2021, 1, 1)


def test_an_unreadable_date_is_refused_with_advice():
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        parse_value("next Tuesday", "date")


@pytest.mark.parametrize("text,expected", [("true", True), ("Yes", True), ("FALSE", False), ("no", False)])
def test_a_boolean_is_true_yes_false_or_no(text, expected):
    assert parse_value(text, "boolean") is expected


def test_any_other_boolean_is_refused():
    with pytest.raises(ValueError, match="true or false"):
        parse_value("maybe", "boolean")


def test_a_string_is_returned_stripped():
    assert parse_value("  Acme  ", "string") == "Acme"


def test_canonical_drops_trailing_zeros_from_a_decimal():
    assert canonical("1,200.50", "decimal") == "1200.5"
    assert canonical("3.000", "decimal") == "3"
    assert canonical("0.0", "decimal") == "0"


def test_canonical_keeps_a_whole_decimal_as_written():
    assert canonical("1100", "decimal") == "1100"


def test_canonical_writes_a_date_in_iso_form():
    assert canonical("14 July 2023", "date") == "2023-07-14"


def test_canonical_writes_booleans_in_lower_case():
    assert canonical("Yes", "boolean") == "true"
    assert canonical("no", "boolean") == "false"


def test_canonical_is_none_for_a_value_that_is_not_of_its_kind():
    assert canonical("abc", "decimal") is None


def test_canonical_is_none_for_infinity_and_nan():
    assert canonical("Infinity", "decimal") is None
    assert canonical("NaN", "decimal") is None


def test_canonical_treats_an_empty_kind_as_string():
    assert canonical(" x ", "") == "x"


def test_number_reads_a_decimal():
    assert number("$1,000.50") == Decimal("1000.5")


def test_number_reads_as_decimal_for_a_non_numeric_kind():
    assert number("12", "string") == Decimal("12")


def test_number_reads_an_integer_kind():
    assert number("1,000", "integer") == Decimal("1000")


def test_number_is_none_for_text():
    assert number("twelve") is None
