"""The call ledger: one record per model call, priced at list price, written to the lake."""

import json

import pytest

from knowledge_store.platform_services.adapters import ledger
from knowledge_store.platform_services.adapters.store import LocalStore


@pytest.fixture
def lake(tmp_path, monkeypatch):
    monkeypatch.setenv("LAKE_URI", str(tmp_path))
    ledger.flush()
    yield LocalStore(tmp_path)
    ledger.flush()


def test_price_key_drops_bedrock_wrapping_and_dates():
    assert ledger.price_key("us.anthropic.claude-haiku-4-5-20251001-v1:0") == "claude-haiku-4-5"
    assert ledger.price_key("") == ""


def test_a_model_without_a_price_costs_none():
    assert ledger.cost_usd("gpt-9", {"inputTokens": 1}) is None
    assert ledger.cost_parts("gpt-9", {}) is None


def test_batch_is_half_price():
    u = {"inputTokens": 1_000_000}
    assert ledger.cost_usd("claude-haiku-4-5", u, tier="batch") == pytest.approx(0.5)


def test_a_bedrock_regional_profile_adds_ten_percent_and_is_marked():
    p = ledger.cost_parts("eu.anthropic.claude-haiku-4-5", {"outputTokens": 1_000_000}, provider="bedrock")
    assert p["usd"] == pytest.approx(5.5) and p["regional"] is True


def test_the_regional_premium_is_bedrock_only():
    assert ledger.cost_usd("eu.anthropic.claude-haiku-4-5", {"outputTokens": 1_000_000}, provider="anthropic") == pytest.approx(5.0)


def test_cache_tokens_are_priced_separately():
    p = ledger.cost_parts("claude-haiku-4-5", {"cacheWriteInputTokens": 1_000_000, "cacheReadInputTokens": 1_000_000})
    assert [x["usd"] for x in p["parts"]] == [0, 0, 1.25, 0.1]


def test_record_carries_the_job_run_and_subject(lake):
    ledger.set_run("extract", "r1")
    with ledger.subject("doc-1"):
        row = ledger.record(provider="anthropic", model_id="claude-haiku-4-5", usage={"inputTokens": 10, "outputTokens": 5})
    assert (row["job"], row["run"], row["subject"]) == ("extract", "r1", "doc-1")
    assert row["cost_usd"] > 0 and row["model_key"] == "claude-haiku-4-5"


def test_the_subject_is_restored_after_its_block(lake):
    with ledger.subject("a"):
        pass
    assert ledger.record(provider="p", model_id="m", usage=None)["subject"] == ""


def test_a_subject_override_wins(lake):
    with ledger.subject("a"):
        assert ledger.record(provider="p", model_id="m", usage=None, subject_override="b")["subject"] == "b"


def test_a_call_without_usage_costs_nothing(lake):
    assert ledger.record(provider="p", model_id="claude-haiku-4-5", usage=None)["cost_usd"] == 0.0


def test_flush_writes_json_lines_under_the_day_and_report_reads_them(lake, monkeypatch):
    ledger.set_run("job a", "run/1")
    ledger.record(provider="anthropic", model_id="claude-haiku-4-5", usage={"inputTokens": 1_000_000})
    ledger.record(provider="anthropic", model_id="claude-haiku-4-5", usage=None, outcome="error")
    ledger.flush()
    keys = list(lake.list("usage/ledger/"))
    assert len(keys) == 1 and "/dt=" in keys[0] and "job_a-run_1-" in keys[0]
    rows = ledger.read(lake)
    assert len(rows) == 2
    assert ledger.read(lake, since="2999-01-01") == []


def test_flush_with_nothing_buffered_writes_nothing(lake):
    ledger.flush()
    assert list(lake.list("usage/")) == []


def test_a_failed_write_is_logged_not_raised(monkeypatch, caplog):
    monkeypatch.setenv("LAKE_URI", "/dev/null/cannot-write-here")
    ledger.record(provider="p", model_id="m", usage=None)
    ledger.flush()
    assert any("ledger write failed" in r.message for r in caplog.records)


def test_summarise_groups_and_prices_per_subject():
    rows = [{"job": "a", "cost_usd": 1.0, "input_tokens": 3, "subject": "s1", "outcome": "ok"},
            {"job": "a", "cost_usd": 2.0, "input_tokens": 1, "subject": "s2", "outcome": "error"},
            {"job": "b", "cost_usd": 0.5, "outcome": "throttled"}]
    out = ledger.summarise(rows, ["job"])
    assert out[0] == {"job": "a", "calls": 2, "failed": 1, "input_tokens": 4, "output_tokens": 0, "cache_write_tokens": 0, "cache_read_tokens": 0, "cost_usd": 3.0, "subjects": 2, "usd_per_subject": 1.5}
    assert out[1]["job"] == "b" and out[1]["failed"] == 1 and out[1]["usd_per_subject"] is None


class _Inner:
    def __init__(self, resp=None, error=None):
        self.resp, self.error = resp, error
        self.other = "passed through"

    def converse(self, **kw):
        if self.error:
            raise self.error
        return self.resp


def test_the_ledger_client_records_each_call(lake):
    c = ledger.LedgerClient(_Inner({"usage": {"inputTokens": 2}, "stopReason": "end_turn"}), "anthropic")
    assert c.converse(modelId="claude-haiku-4-5")["stopReason"] == "end_turn"
    assert c.other == "passed through"
    ledger.flush()
    (row,) = ledger.read(lake)
    assert row["outcome"] == "end_turn" and row["input_tokens"] == 2


@pytest.mark.parametrize("error,outcome", [(RuntimeError("ThrottlingException: slow down"), "throttled"), (RuntimeError("Too many tokens"), "throttled"), (ValueError("bad"), "error")])
def test_a_failed_call_is_recorded_and_raised(lake, error, outcome):
    c = ledger.LedgerClient(_Inner(error=error), "bedrock")
    with pytest.raises(type(error)):
        c.converse(modelId="m")
    ledger.flush()
    (row,) = ledger.read(lake)
    assert row["outcome"] == outcome and row["error"]


def test_report_prints_a_summary_and_total(lake, capsys):
    ledger.set_run("j", "r9")
    ledger.record(provider="p", model_id="claude-haiku-4-5", usage={"inputTokens": 1_000_000})
    ledger.flush()
    assert ledger.main(["report", "--run", "r9", "--store", str(lake.root), "--by", "job"]) == 0
    lines = [json.loads(x) for x in capsys.readouterr().out.splitlines()]
    assert lines[-1] == {"total_calls": 1, "total_cost_usd": 1.0}
