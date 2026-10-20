"""Ingestion domain: passage chunking."""

from knowledge_store.ingestion.domain.chunk import CHUNKER_VERSION, Passage, chunk_text

DOC = "d" * 64


def test_an_empty_text_has_no_passages():
    assert chunk_text("", DOC) == []


def test_blank_paragraphs_are_dropped():
    assert chunk_text("\n\n   \n\n", DOC) == []


def test_a_short_text_is_one_passage():
    ps = chunk_text("One paragraph.\n\nAnother paragraph.", DOC)
    assert len(ps) == 1
    assert ps[0].text == "One paragraph.\n\nAnother paragraph."
    assert ps[0].seq == 0 and ps[0].doc_id == DOC


def test_passage_ids_are_stable_for_the_same_text():
    text = "Alpha beta.\n\nGamma delta."
    assert [p.passage_id for p in chunk_text(text, DOC)] == [p.passage_id for p in chunk_text(text, DOC)]


def test_a_passage_id_carries_the_document_prefix_the_sequence_and_a_hash():
    p = chunk_text("Some text here.", DOC)[0]
    prefix, seq, digest = p.passage_id.split("-")
    assert prefix == DOC[:16] and seq == "p000" and digest == p.content_hash[:10]


def test_the_content_hash_ignores_whitespace_differences():
    a = chunk_text("one  two\tthree", DOC)[0]
    b = chunk_text("one two three", DOC)[0]
    assert a.content_hash == b.content_hash


def test_a_changed_text_changes_the_passage_id():
    assert chunk_text("one", DOC)[0].passage_id != chunk_text("two", DOC)[0].passage_id


def test_paragraphs_pack_up_to_the_target():
    paras = ["word " * 30] * 10  # 150 chars each
    ps = chunk_text("\n\n".join(paras), DOC, target=400, max_chars=1000)
    assert len(ps) > 1
    assert all(len(p.text) <= 1000 for p in ps)


def test_sequences_count_up_from_zero():
    ps = chunk_text("\n\n".join(["x" * 100] * 6), DOC, target=150, max_chars=300)
    assert [p.seq for p in ps] == list(range(len(ps)))


def test_offsets_point_at_the_passage_in_the_source_text():
    text = "First block.\n\nSecond block."
    for p in chunk_text(text, DOC, target=5, max_chars=50):
        assert text[p.char_start:p.char_end].strip() == p.text


def test_a_long_paragraph_splits_on_line_boundaries_never_inside_a_line():
    lines = [f"row {i} | {'v' * 40}" for i in range(40)]
    text = "\n".join(lines)
    ps = chunk_text(text, DOC, target=300, max_chars=500)
    assert len(ps) > 1
    for p in ps:
        for line in p.text.splitlines():
            assert line in lines


def test_a_single_overlong_line_splits_on_whitespace():
    text = " ".join(["token"] * 500)  # one line, ~3000 chars
    ps = chunk_text(text, DOC, target=200, max_chars=400)
    assert len(ps) > 1
    assert all(len(p.text) <= 400 for p in ps)
    assert " ".join(" ".join(p.text for p in ps).split()) == text


def test_a_line_with_no_whitespace_is_cut_at_the_limit():
    text = "x" * 1000
    ps = chunk_text(text, DOC, target=100, max_chars=300)
    assert "".join(p.text for p in ps) == text
    assert all(len(p.text) <= 300 for p in ps)


def test_a_passage_round_trips_through_a_dict():
    p = chunk_text("Round trip.", DOC)[0]
    assert Passage.from_dict({**p.to_dict(), "extra": 1}) == p


def test_the_chunker_has_a_version():
    assert CHUNKER_VERSION == "chunk@1"
