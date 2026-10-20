"""Figures in an answer: what a text states, and whether it states the expected figure at its
own rounding."""

from __future__ import annotations

from decimal import Decimal

import pytest

from knowledge_store.evaluation.domain.numeric import matches, stated


def test_a_plain_number_is_stated_to_its_last_digit():
    assert stated("there were 42 of them") == [(Decimal(42), Decimal("0.5"))]


def test_decimals_narrow_the_rounding():
    assert stated("3.14") == [(Decimal("3.14"), Decimal("0.005"))]


def test_thousands_separators_are_read():
    assert stated("1,234,567 units")[0][0] == Decimal(1234567)


@pytest.mark.parametrize("text,value", [("2.2 billion", Decimal("2.2e9")), ("2.2bn", Decimal("2.2e9")), ("5k", Decimal(5000)),
                                        ("7 million", Decimal(7e6)), ("4 mn", Decimal(4e6)), ("1 trillion", Decimal(1e12)),
                                        ("3 thousand", Decimal(3000)), ("2 tn", Decimal(2e12))])
def test_scale_words_multiply(text, value):
    assert stated(text)[0][0] == value


def test_a_scaled_figure_is_stated_to_the_scale_of_its_last_digit():
    assert stated("$2.2 billion") == [(Decimal("2.2e9"), Decimal("5e7"))]


def test_a_minus_or_bracket_makes_a_number_negative():
    assert stated("-5")[0][0] == Decimal(-5)
    assert stated("(0.12)")[0][0] == Decimal("-0.12")


def test_a_year_is_not_a_figure():
    assert stated("In 2024 and 1999") == []


def test_a_four_digit_number_outside_the_year_range_is_a_figure():
    assert stated("1850 tonnes")[0][0] == Decimal(1850)
    assert stated("2500 tonnes")[0][0] == Decimal(2500)


def test_a_year_with_a_scale_or_decimals_is_a_figure():
    assert stated("2024 million")[0][0] == Decimal("2.024e9")
    assert stated("2024.5")[0][0] == Decimal("2024.5")


def test_digits_inside_a_word_are_not_numbers():
    assert stated("A320neo and B737") == []


def test_empty_or_missing_text_states_nothing():
    assert stated("") == [] and stated(None) == []


def test_every_number_in_the_text_is_found():
    assert [v for v, _ in stated("up from 2.4 to 2.6 billion, 12%")] == [Decimal("2.4"), Decimal("2.6e9"), Decimal(12)]


def test_the_expected_figure_matches_within_half_a_unit_of_the_stated_digit():
    assert matches("$94.9 billion", 94_949_999_999)
    assert not matches("$94.9 billion", 94_960_000_000)


def test_a_round_expected_figure_does_not_widen_the_window():
    assert not matches("$2.6 billion", 3_000_000_000)


def test_any_stated_number_can_match():
    assert matches("from 2.4 billion to 3 billion", 3e9)


def test_a_relative_tolerance_replaces_the_rounding():
    assert matches("3.1 billion", 3e9, tolerance=0.05)
    assert not matches("3.2 billion", 3e9, tolerance=0.05)


def test_a_relative_tolerance_of_zero_needs_the_exact_figure():
    assert matches("3,000,000,000", 3e9, tolerance=0)
    assert not matches("3.0 billion and 2,999,999,999", 2.9e9, tolerance=0)


def test_a_negative_figure_matches_only_a_negative_statement():
    assert matches("a loss of -1.5 million", -1.5e6)
    assert not matches("1.5 million", -1.5e6)


def test_nothing_stated_matches_nothing():
    assert not matches("no numbers here", 0)
