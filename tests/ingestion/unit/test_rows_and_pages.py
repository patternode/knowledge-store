"""Ingestion domain: table rows stay whole, and PDF pages stay apart."""

from knowledge_store.ingestion.domain.chunk import chunk_document, chunk_regions
from knowledge_store.ingestion.domain.conform import conform
from knowledge_store.ingestion.domain.delimited import table_text
from knowledge_store.ingestion.domain.parsing import ParseResult
from knowledge_store.ingestion.domain.steps import silver_body

DOC = "d" * 64


def _cells(line: str) -> list[str]:
    return line.split(" | ")


def test_duplicate_rows_keep_their_own_offsets():
    text = "id: 1\nid: 1\nid: 1"
    passages = chunk_document(text, DOC, parser="table@1", target=4, max_chars=20)
    assert [p.text for p in passages] == ["id: 1", "id: 1", "id: 1"]
    assert [p.char_start for p in passages] == [0, 6, 12]
    assert [p.seq for p in passages] == [0, 1, 2]
    assert len({p.passage_id for p in passages}) == 3


def test_blank_lines_between_rows_are_not_passages():
    text = "id: 1\n\n\nid: 2"
    passages = chunk_document(text, DOC, parser="table@1", target=4, max_chars=20)
    assert [p.text for p in passages] == ["id: 1", "id: 2"]
    assert [text[p.char_start:p.char_end].strip() for p in passages] == [p.text for p in passages]


def test_short_rows_pack_up_to_the_target_and_a_row_is_never_cut():
    rows = [f"id: {i} | note: {'x' * 40}" for i in range(8)]
    text = "\n".join(rows)
    passages = chunk_document(text, DOC, parser="table@1", target=100, max_chars=300)
    assert len(passages) > 1
    seen = []
    for passage in passages:
        assert text[passage.char_start:passage.char_end].strip() == passage.text
        for line in passage.text.splitlines():
            assert line in rows
            seen.append(line)
    assert seen == rows


def test_a_long_row_breaks_between_cells_and_the_cells_come_back_in_order():
    cells = [f"c{i}: " + ("abcd " * 6).strip() for i in range(8)]
    line = " | ".join(cells)
    passages = chunk_document(line, DOC, parser="table@1", target=30, max_chars=80)
    collected = []
    for passage in passages:
        assert len(passage.text) <= 80
        assert not passage.text.startswith("|") and not passage.text.endswith("|")
        assert line[passage.char_start:passage.char_end].strip() == passage.text
        collected.extend(_cells(passage.text))
    assert collected == cells


def test_a_cell_longer_than_the_cap_splits_without_swallowing_the_next_cell():
    line = "code: A1 | " + ("word " * 40).strip() + " | tail: end"
    passages = chunk_document(line, DOC, parser="table@1", target=1, max_chars=48)
    assert passages[0].text == "code: A1"
    assert passages[-1].text == "tail: end"
    middle = " ".join(passages[i].text for i in range(1, len(passages) - 1))
    assert "code: A1" not in middle and "tail: end" not in middle
    assert all(len(p.text) <= 48 for p in passages)


def test_a_sentence_inside_a_row_does_not_split_the_row():
    line = "note: See you. Then later. The row stays one passage."
    passages = chunk_document(line, DOC, parser="table@1", target=10, max_chars=200)
    assert [p.text for p in passages] == [line]


def test_an_escaped_separator_is_not_a_cell_boundary():
    rendered, _ = table_text('note,more\n"left | right stays",tail\n', tab=False)
    passages = chunk_document(rendered, DOC, parser="table@1", target=10, max_chars=24)
    assert [p.text for p in passages] == ["note: left / right stays", "more: tail"]


def test_row_passage_ids_repeat_for_the_same_text():
    text = "id: 1 | name: Ada\nid: 2 | name: Grace"
    assert [p.passage_id for p in chunk_document(text, DOC, parser="table@1")] == [
        p.passage_id for p in chunk_document(text, DOC, parser="table@1")]


def test_pages_are_conformed_apart_and_their_rules_are_added():
    page_a = "Paid $1,200.50 and $2,000.00 and $3,000.00 and $4,000.00 here."
    page_b = "Paid $5,000.00 on 14 July 2023 and then $6.50."
    parsed = ParseResult("raw join that must not be used", "14 July 2023", "pdf@1",
                         {"pages": 3}, (page_a, "   ", page_b))
    one, two = conform(page_a), conform(page_b)
    body = silver_body(parsed, DOC)
    assert body.text == one.text + "\n\n" + two.text
    assert "raw join" not in body.text
    assert body.title == "2023-07-14"
    assert [p.text for p in body.passages] == [one.text, two.text]
    assert body.passages[0].char_end <= len(one.text)
    assert body.passages[1].char_start == len(one.text) + 2
    for passage in body.passages:
        assert body.text[passage.char_start:passage.char_end].strip() == passage.text
    merged = {row["rule"]: row for row in body.rules}
    unique = []
    for source in (one, two):
        for row in source.rules:
            applied = sum(item["applied"] for src in (one, two) for item in src.rules if item["rule"] == row["rule"])
            assert merged[row["rule"]]["applied"] == applied
            if row["rule"] == "number":
                for example in row["examples"]:
                    if example not in unique:
                        unique.append(example)
    assert len(unique) > 3
    assert merged["number"]["examples"] == unique[:3]
    assert "date" in merged


def test_a_long_page_splits_inside_itself_and_the_next_page_stays_whole():
    first = " ".join(f"Sentence {i}." for i in range(40))
    second = "Only the second page."
    text = first + "\n\n" + second
    regions = [(0, len(first)), (len(first) + 2, len(text))]
    passages = chunk_regions(text, regions, DOC, parser="pdf@1", target=60, max_chars=80)
    assert len(passages) > 2
    assert passages[-1].text == second
    assert all("Sentence" not in p.text for p in passages[-1:])
    assert all(second not in p.text for p in passages[:-1])
    assert [p.seq for p in passages] == list(range(len(passages)))
    assert passages[0].passage_id != passages[1].passage_id
    assert all(p.passage_id.startswith(DOC[:16] + "-p") for p in passages)
    for passage in passages:
        assert text[passage.char_start:passage.char_end].strip() == passage.text


def test_one_part_is_the_document_and_blank_parts_add_nothing():
    parsed = ParseResult("wrong", None, "pdf@1", parts=("Paid $1,200.50 today.",))
    body = silver_body(parsed, DOC)
    assert body.text == "Paid $1200.50 today."
    assert body.passages[0].text == body.text
    blank = silver_body(ParseResult("ignored", None, "pdf@1", parts=("  ", "")), DOC)
    assert blank.text == "" and blank.passages == [] and blank.rules == ()


def test_a_document_without_parts_is_conformed_as_one_piece():
    parsed = ParseResult("See you on 14 July 2023.", "Notes", "text@1")
    body = silver_body(parsed, DOC)
    assert body.text == "See you on 2023-07-14."
    assert body.title == "Notes"
    assert len(body.passages) == 1


def test_a_table_row_is_conformed_inside_the_row_and_stays_one_passage():
    parsed = ParseResult(
        'amount: $1,200.50 | when: 14 July 2023 | note: See you. Then later.',
        "Quarterly note", "table@1")
    body = silver_body(parsed, DOC)
    assert body.passages[0].text == "amount: $1200.50 | when: 2023-07-14 | note: See you. Then later."
    assert body.text == body.passages[0].text
    assert conform(body.text).text == body.text
