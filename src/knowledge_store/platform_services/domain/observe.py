"""Production measures from answer traces: what can be measured without labelled answers.

    answers by outcome      answered, declined, failed: a rising failure or decline rate is the first sign
    latency                 p50 and p95 of an answer's time, in milliseconds
    cost                    per answer and in total, from the trace's cost (the ledger's prices)
    retrieval empty rate    answers whose tools returned nothing: coverage
    unsupported share       claims the support check labelled unsupported, of the claims checked

Pure: a list of traces in, one summary out. Relevance and support on a sample are measured
offline (patternode-architecture considerations/ai-context-platform-gaps.md, step 5).
"""

from __future__ import annotations


def _pct(xs: list[float], p: float) -> float | None:
    if not xs:
        return None
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p * (len(xs) - 1))))]


def _cost(t: dict) -> float:
    c = t.get("cost")
    if isinstance(c, dict):
        return float(c.get("usd") or c.get("total_usd") or 0.0)
    return float(c or 0.0)


def summarise(traces: list[dict]) -> dict:
    n = len(traces)
    outcomes: dict[str, int] = {}
    for t in traces:
        outcomes[t.get("outcome", "unknown")] = outcomes.get(t.get("outcome", "unknown"), 0) + 1
    ms = [float(t["ms"]) for t in traces if t.get("ms") is not None]
    checked = [c for t in traces for c in t.get("claims") or [] if c.get("support") in ("supported", "unsupported")]
    cost = round(sum(_cost(t) for t in traces), 4)
    return {
        "answers": n, "outcomes": outcomes,
        "failed_share": round(outcomes.get("failed", 0) / n, 3) if n else None,
        "declined_share": round(outcomes.get("declined", 0) / n, 3) if n else None,
        "latency_ms_p50": _pct(ms, 0.5), "latency_ms_p95": _pct(ms, 0.95),
        "cost_usd": cost, "cost_usd_per_answer": round(cost / n, 4) if n else None,
        "retrieval_empty_share": round(sum(1 for t in traces if not t.get("retrieved")) / n, 3) if n else None,
        "unsupported_share": round(sum(c["support"] == "unsupported" for c in checked) / len(checked), 3) if checked else None,
    }
