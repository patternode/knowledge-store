"""kernel.identifiers: only plain identifiers reach query text."""

import pytest

from knowledge_store.kernel.identifiers import safe_name


@pytest.mark.parametrize("name", ["Company", "_private", "has_part2", "A"])
def test_a_plain_identifier_is_returned_unchanged(name):
    assert safe_name(name) == name


@pytest.mark.parametrize("name", ["", "2nd", "a-b", "a b", "x`) DETACH DELETE n //", "naïve", "a.b"])
def test_anything_else_is_refused(name):
    with pytest.raises(ValueError, match="plain identifier"):
        safe_name(name)


def test_a_trailing_newline_is_refused():
    # re's $ matches before a final newline; the name must still be rejected or it lands in a query.
    with pytest.raises(ValueError):
        safe_name("Company\n")
