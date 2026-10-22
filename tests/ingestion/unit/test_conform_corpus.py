"""The cited EnterpriseRAG documents, when the directory is available.

Set ENTERPRISE_RAG_DOCUMENTS to the documents directory. The lab keeps that set in
patternode-platform, so a knowledge-store checkout does not carry it and this test skips.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from knowledge_store.ingestion.domain.conform import conform

_PHONE = re.compile(r"\+\d(?: \d{3}){2,}(?: \d+)?")
_PAREN_AMOUNT = re.compile(r"\(\d+\.\d+%?\)")

pytestmark = pytest.mark.skipif(
    not os.environ.get("ENTERPRISE_RAG_DOCUMENTS"),
    reason="ENTERPRISE_RAG_DOCUMENTS is not set",
)


def test_every_cited_document_conforms_once_and_keeps_no_control_characters():
    root = Path(os.environ["ENTERPRISE_RAG_DOCUMENTS"])
    paths = sorted(root.rglob("*.txt"))
    assert paths, f"no documents under {root}"
    for path in paths:
        source = path.read_text(encoding="utf-8")
        once = conform(source)
        twice = conform(once.text)
        assert twice.text == once.text and twice.rules == (), path.name
        assert not any(unicat(ch) for ch in once.text), path.name
        for phone in _PHONE.findall(source):
            assert once.text.count(phone) == source.count(phone), path.name
        for amount in _PAREN_AMOUNT.findall(source):
            assert once.text.count(amount) == source.count(amount), path.name


def unicat(ch: str) -> bool:
    import unicodedata
    if ch in "\t\n":
        return False
    return unicodedata.category(ch) in ("Cc", "Cs")
