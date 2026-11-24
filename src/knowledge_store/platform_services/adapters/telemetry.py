"""Live metrics for each answer, on open standards.

Where the OpenTelemetry API is installed (the agent's image runs under the AWS Distro for
OpenTelemetry, which sends to CloudWatch; any OTLP backend works the same way, chosen by the
OTEL_* environment), each answer adds to these instruments:

    ks.answers                 counter, by outcome and collection
    ks.answer.duration         histogram, milliseconds
    ks.answer.cost             counter, US dollars at list price
    ks.retrieval.empty         counter, answers whose tools returned nothing
    ks.claims                  counter, by support verdict
    gen_ai.client.token.usage  histogram, by gen_ai.token.type and gen_ai.request.model (OpenTelemetry's
                               semantic conventions for generative AI)

Where it is not (the portal's Lambda), and TELEMETRY_EMF is set, the same figures are printed as
one CloudWatch embedded-metric line per answer, which CloudWatch Logs turns into metrics in the
KnowledgeStore namespace. Telemetry never fails an answer.
"""

from __future__ import annotations

import json
import logging
import os
import time

log = logging.getLogger("telemetry")
NAMESPACE = "KnowledgeStore"
_instruments: dict | None = None


def _otel() -> dict | None:
    global _instruments
    if _instruments is not None:
        return _instruments or None
    try:
        from opentelemetry import metrics
    except ImportError:
        _instruments = {}
        return None
    m = metrics.get_meter("knowledge_store")
    _instruments = {
        "answers": m.create_counter("ks.answers", unit="1", description="Answers by outcome"),
        "duration": m.create_histogram("ks.answer.duration", unit="ms", description="Time to answer"),
        "cost": m.create_counter("ks.answer.cost", unit="USD", description="List-price cost of answers"),
        "empty": m.create_counter("ks.retrieval.empty", unit="1", description="Answers whose tools returned nothing"),
        "claims": m.create_counter("ks.claims", unit="1", description="Claims shown, by support verdict"),
        "tokens": m.create_histogram("gen_ai.client.token.usage", unit="{token}", description="Tokens per answer"),
    }
    return _instruments


def _usd(trace: dict) -> float:
    c = trace.get("cost")
    return float((c.get("usd") or c.get("total_usd") or 0.0) if isinstance(c, dict) else (c or 0.0))


def emf_line(trace: dict) -> str:
    """One CloudWatch embedded-metric record for an answer."""
    claims = trace.get("claims") or []
    figures = {"Answers": 1, "LatencyMs": float(trace.get("ms") or 0), "CostUsd": _usd(trace),
               "RetrievalEmpty": 0 if trace.get("retrieved") else 1,
               "UnsupportedClaims": sum(c.get("support") == "unsupported" for c in claims),
               "Failed": 1 if trace.get("outcome") == "failed" else 0}
    units = {"LatencyMs": "Milliseconds", "CostUsd": "None"}
    return json.dumps({"_aws": {"Timestamp": int(time.time() * 1000), "CloudWatchMetrics": [{
        "Namespace": NAMESPACE, "Dimensions": [["Outcome"], []],
        "Metrics": [{"Name": k, "Unit": units.get(k, "Count")} for k in figures]}]},
        "Outcome": trace.get("outcome", "unknown"), **figures})


def emit(trace: dict) -> None:
    try:
        inst = _otel()
        if inst:
            attrs = {"outcome": trace.get("outcome", "unknown"), "collection": trace.get("collection") or ""}
            inst["answers"].add(1, attrs)
            if trace.get("ms") is not None:
                inst["duration"].record(float(trace["ms"]), attrs)
            inst["cost"].add(_usd(trace), attrs)
            if not trace.get("retrieved"):
                inst["empty"].add(1, attrs)
            for c in trace.get("claims") or []:
                inst["claims"].add(1, {"support": c.get("support", "unchecked")})
            usage = trace.get("usage") or {}
            for kind, key in (("input", "inputTokens"), ("output", "outputTokens")):
                if usage.get(key):
                    inst["tokens"].record(usage[key], {"gen_ai.token.type": kind,
                                                       "gen_ai.request.model": trace.get("model") or ""})
        elif os.environ.get("TELEMETRY_EMF"):
            print(emf_line(trace), flush=True)
    except Exception:  # noqa: BLE001, telemetry never fails an answer
        log.exception("telemetry not emitted")
