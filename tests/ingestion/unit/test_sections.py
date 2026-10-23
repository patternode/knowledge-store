"""Ingestion domain: sections before passages are packed."""

from knowledge_store.ingestion.domain.chunk import (
    CHUNKER_VERSION, SECTION_CHUNKER, chunk_document, chunk_text,
)
from knowledge_store.ingestion.domain.sections import sections

DOC = "d" * 64


def test_plain_text_is_one_section():
    text = "Alpha.\n\nBeta."
    spans = sections(text, headings=False)
    assert [(s.kind, text[s.start:s.end]) for s in spans] == [("prose", text)]


def test_a_markdown_heading_starts_a_section_and_a_fence_stays_whole():
    text = "# One\n\nAlpha.\n\n```\n# not a heading\n```\n\n# Two\n\nBeta."
    spans = sections(text, headings=True)
    bodies = [text[s.start:s.end] for s in spans]
    assert bodies[0].startswith("# One") and "Alpha." in bodies[0]
    assert any(s.kind == "fence" and "# not a heading" in text[s.start:s.end] for s in spans)
    assert bodies[-1].startswith("# Two") and "Beta." in bodies[-1]
    assert "Beta." not in bodies[0]


def test_a_setext_heading_starts_a_section():
    text = "Costs\n====\n\nRent."
    spans = sections(text, headings=True)
    assert len(spans) == 1
    assert text[spans[0].start:spans[0].end].startswith("Costs")


def test_plain_text_passages_match_the_paragraph_chunker():
    text = "One paragraph.\n\nAnother paragraph.\n\nThird."
    assert [p.text for p in chunk_document(text, DOC, parser="text@1")] == [
        p.text for p in chunk_text(text, DOC)]
    assert CHUNKER_VERSION == "chunk@1" and SECTION_CHUNKER == "chunk@2"


def test_a_heading_stays_with_its_body_and_the_next_heading_does_not():
    text = "# Costs\n\nRent was due.\n\n# Tax\n\nFiled."
    passages = chunk_document(text, DOC, parser="markdown@1")
    assert [p.text for p in passages] == ["# Costs\n\nRent was due.", "# Tax\n\nFiled."]
    assert [p.seq for p in passages] == [0, 1]


def test_an_oversized_section_splits_on_sentences_and_keeps_the_heading():
    body = " ".join(["Sentence number %d." % i for i in range(40)])
    text = "# Notes\n\n" + body
    passages = chunk_document(text, DOC, parser="markdown@1", target=80, max_chars=120)
    assert passages[0].text.startswith("# Notes")
    assert all(len(p.text) <= 120 for p in passages)
    assert "Sentence number 0." in passages[0].text
    joined = " ".join(p.text for p in passages)
    assert "# Notes" in joined and "Sentence number 39." in joined


def test_a_fence_is_not_split_across_the_prose_around_it():
    text = "Before.\n\n```\nline one\nline two\n```\n\nAfter."
    passages = chunk_document(text, DOC, parser="markdown@1", target=5, max_chars=50)
    fence = next(p for p in passages if "line one" in p.text)
    assert "line two" in fence.text
    assert "Before." not in fence.text and "After." not in fence.text


def test_html_headings_pack_as_sections():
    from knowledge_store.ingestion.domain.parsers import parse_html
    parsed = parse_html(b"<h2>Costs</h2><p>Rent was due.</p><h2>Tax</h2><p>Filed.</p>")
    passages = chunk_document(parsed.text, DOC, parser=parsed.parser)
    assert [p.text for p in passages] == ["## Costs\n\nRent was due.", "## Tax\n\nFiled."]
