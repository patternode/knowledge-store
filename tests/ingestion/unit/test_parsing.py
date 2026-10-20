"""Ingestion domain: the parsing facade refine uses."""

from knowledge_store.ingestion.domain import parsers, parsing


def test_parsing_publishes_the_parsers_names():
    assert parsing.parse is parsers.parse
    assert parsing.UnsupportedFormat is parsers.UnsupportedFormat
    assert parsing.PARSERS is parsers.PARSERS
    assert set(parsing.__all__) == {"PARSERS", "ParseResult", "UnsupportedFormat", "parse"}
