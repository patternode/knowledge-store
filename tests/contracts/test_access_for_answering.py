"""What Answering relies on from Access's contract: the per-person daily limit."""

from __future__ import annotations

from contract_support import published
from knowledge_store import access


def test_answering_finds_what_it_uses():
    published("access", ["agent_quota"])


def test_the_limit_is_off_unless_configured(monkeypatch):
    monkeypatch.delenv("AGENT_QUOTA_TABLE", raising=False)
    assert access.agent_quota.AgentQuota.from_env() is None


def test_a_caller_with_no_subject_is_refused():
    class Table:
        def update_item(self, **kw):
            raise AssertionError("never counted")
    q = access.agent_quota.AgentQuota("t", 5, table=Table())
    assert q.check("not-a-jwt") == "the caller's token names no subject"


def test_the_limit_message_is_published():
    assert access.agent_quota.LIMIT_REACHED
