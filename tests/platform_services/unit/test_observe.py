"""Production measures from answer traces, and the live metrics each answer emits."""

import json

from knowledge_store.platform_services import observe
from knowledge_store.platform_services.adapters import telemetry


def t(outcome="answered", ms=1000, cost=0.01, retrieved=True, supports=("supported",)):
    return {"outcome": outcome, "ms": ms, "cost": {"usd": cost}, "retrieved": [{"id": "p"}] if retrieved else [],
            "claims": [{"support": s} for s in supports], "collection": "m"}


def test_the_summary_counts_outcomes_latency_cost_and_quality():
    s = observe.summarise([t(), t(ms=3000), t("failed", ms=500, supports=()), t("declined", retrieved=False, supports=()),
                           t(supports=("unsupported", "supported"))])
    assert s["answers"] == 5 and s["outcomes"] == {"answered": 3, "failed": 1, "declined": 1}
    assert s["failed_share"] == 0.2 and s["latency_ms_p95"] == 3000 and s["retrieval_empty_share"] == 0.2
    assert s["unsupported_share"] == 0.25 and s["cost_usd"] == 0.05


def test_an_empty_day_is_reported_without_dividing_by_zero():
    assert observe.summarise([])["answers"] == 0


def test_an_answer_prints_one_embedded_metric_line_where_open_telemetry_is_absent(monkeypatch, capsys):
    monkeypatch.setattr(telemetry, "_otel", lambda: None)
    monkeypatch.setenv("TELEMETRY_EMF", "1")
    telemetry.emit(t("failed", supports=("unsupported",)))
    rec = json.loads(capsys.readouterr().out)
    assert rec["_aws"]["CloudWatchMetrics"][0]["Namespace"] == "KnowledgeStore"
    assert rec["Failed"] == 1 and rec["UnsupportedClaims"] == 1 and rec["Outcome"] == "failed"


def test_telemetry_never_raises(monkeypatch):
    monkeypatch.setattr(telemetry, "_otel", lambda: (_ for _ in ()).throw(RuntimeError("exporter down")))
    telemetry.emit(t())
