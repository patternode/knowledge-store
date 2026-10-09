"""The call ledger: one record per model call, with its tokens and list-price cost.

Every model call in the lab goes through llm.runtime_client(), which records each
`converse` here, on either provider. Batch first turns are recorded by extract_batch
when finish uses them, at the batch price. Records carry the job, run and subject
(the release or call) that were current when the call was made, so cost can be
summed per run, per step and per company.

Records are buffered and written to the lake as JSON lines under
usage/ledger/dt=<date>/<job>-<run>-<id>.jsonl, every FLUSH_EVERY records and when the
process exits. Without a lake (LAKE_URI unset) they go under LEDGER_ROOT (default build) locally. A
write that fails is logged as the records themselves, so nothing is lost and no model
call ever fails because of the ledger.

Cost is the list price for the tokens (see PRICES), not the bill: it leaves out
credits, discounts and tax. Bedrock regional inference profiles (us., eu., ...) carry
AWS's 10% premium over global ones for Claude 4.5 and later.

  python -m knowledge_store.ledger report --run <run id> [--since 2026-09-27] [--by job,model,tier]
"""

from __future__ import annotations

import argparse
import atexit
import contextlib
import contextvars
import datetime as dt
import json
import logging
import os
import re
import threading
import time
import uuid
from collections import defaultdict

log = logging.getLogger("ledger")

PREFIX = "usage/ledger"
FLUSH_EVERY = int(os.environ.get("LEDGER_FLUSH_EVERY", "200"))

# USD per million tokens: input, output, 5-minute cache write, cache read. Claude API list
# prices, checked 2026-09-27 (platform.claude.com/docs/en/about-claude/pricing). Batch is
# half of each. Keyed by the model family and version, with any date suffix dropped.
PRICES = {
    "claude-fable-5-1": (10.0, 50.0, 12.5, 0.25),
    "claude-fable-5": (10.0, 50.0, 12.5, 1.0),
    "claude-opus-5-5": (4.0, 20.0, 5.0, 0.20),
    "claude-opus-5": (5.0, 25.0, 6.25, 0.50),
    "claude-opus-4-8": (5.0, 25.0, 6.25, 0.50),
    "claude-opus-4-7": (5.0, 25.0, 6.25, 0.50),
    "claude-opus-4-6": (5.0, 25.0, 6.25, 0.50),
    "claude-opus-4-5": (5.0, 25.0, 6.25, 0.50),
    "claude-sonnet-5": (2.0, 10.0, 2.5, 0.20),
    "claude-sonnet-4-6": (3.0, 15.0, 3.75, 0.30),
    "claude-sonnet-4-5": (3.0, 15.0, 3.75, 0.30),
    "claude-haiku-4-5": (1.0, 5.0, 1.25, 0.10),
}
_DATE = re.compile(r"[-@]\d{8}$")
_REGIONAL = re.compile(r"^(?:us|eu|apac|jp|au)\.anthropic\.")

_job = contextvars.ContextVar("ledger_job", default=os.environ.get("LEDGER_JOB", ""))
_run = contextvars.ContextVar("ledger_run", default=os.environ.get("LEDGER_RUN", ""))
_subject = contextvars.ContextVar("ledger_subject", default="")


def set_run(job: str, run: str | None) -> None:
    """The job and run for every call this process makes from here on."""
    _job.set(job)
    _run.set(run or "")


@contextlib.contextmanager
def subject(value: str):
    """The release, call or case the calls inside this block are for."""
    token = _subject.set(value or "")
    try:
        yield
    finally:
        _subject.reset(token)


def price_key(model_id: str) -> str:
    from .llm import model_name
    return _DATE.sub("", model_name(model_id or ""))


# (key, label, Converse usage field, index into a PRICES row)
_PARTS = (
    ("input", "Input tokens", "inputTokens", 0),
    ("output", "Output tokens", "outputTokens", 1),
    ("cache_write", "Cache write", "cacheWriteInputTokens", 2),
    ("cache_read", "Cache read", "cacheReadInputTokens", 3),
)


def _scale(model_id: str, tier: str, provider: str) -> float:
    scale = 0.5 if tier == "batch" else 1.0
    if provider == "bedrock" and _REGIONAL.match(model_id or ""):
        scale *= 1.1
    return scale


def cost_parts(model_id: str, usage: dict, *, tier: str = "standard", provider: str = "anthropic") -> dict | None:
    """List-price cost of one call, split by where the tokens were spent, or None for a model
    with no price here. usage uses Converse field names. The total is the list price: credits,
    discounts and tax are not included. A Bedrock regional inference profile adds 10%."""
    p = PRICES.get(price_key(model_id))
    if not p:
        return None
    scale = _scale(model_id, tier, provider)
    parts, total = [], 0.0
    for key, label, field, i in _PARTS:
        tokens = int((usage or {}).get(field) or 0)
        usd = tokens * p[i] * scale / 1e6
        total += usd
        parts.append({"key": key, "label": label, "tokens": tokens, "usd": round(usd, 6)})
    return {"usd": round(total, 6), "parts": parts, "model_id": model_id, "provider": provider,
            "regional": bool(provider == "bedrock" and _REGIONAL.match(model_id or ""))}


def cost_usd(model_id: str, usage: dict, *, tier: str = "standard", provider: str = "anthropic") -> float | None:
    """List-price cost of one call's usage (Converse field names), or None for a model
    with no price here."""
    parts = cost_parts(model_id, usage, tier=tier, provider=provider)
    return None if parts is None else parts["usd"]


class _Buffer:
    def __init__(self):
        self.lock = threading.Lock()
        self.rows: list[dict] = []
        self.part = uuid.uuid4().hex[:8]
        self.seq = 0

    def add(self, row: dict) -> None:
        with self.lock:
            self.rows.append(row)
            full = len(self.rows) >= FLUSH_EVERY
        if full:
            self.flush()

    def flush(self) -> None:
        with self.lock:
            rows, self.rows = self.rows, []
            self.seq += 1
            seq = self.seq
        if not rows:
            return
        body = "\n".join(json.dumps(r, default=str) for r in rows) + "\n"
        day = rows[0]["ts"][:10]
        name = f"{_safe(rows[0]['job'] or 'job')}-{_safe(rows[0]['run'] or 'norun')}-{self.part}-{seq:04d}.jsonl"
        try:
            from .store import store_from_uri
            store_from_uri(_root()).put(f"{PREFIX}/dt={day}/{name}", body.encode(), "application/x-ndjson")
        except Exception as e:  # noqa: BLE001, the ledger never breaks a model call
            log.warning("ledger write failed (%s: %s); records follow", type(e).__name__, str(e)[:200])
            for r in rows:
                log.warning("ledger %s", json.dumps(r, default=str))


def _root() -> str:
    """The lake, or without one a local directory (LEDGER_ROOT, default build)."""
    return os.environ.get("LAKE_URI") or os.environ.get("LEDGER_ROOT", "build")


def _safe(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", s)[:60]


_buffer = _Buffer()
atexit.register(_buffer.flush)


def flush() -> None:
    """Write buffered records now (a Lambda or a long-lived process should call this)."""
    _buffer.flush()


def record(*, provider: str, model_id: str, usage: dict | None, tier: str = "standard",
           latency_s: float | None = None, outcome: str = "ok", error: str | None = None,
           subject_override: str | None = None) -> dict:
    usage = usage or {}
    row = {"ts": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
           "job": _job.get(), "run": _run.get(),
           "subject": subject_override if subject_override is not None else _subject.get(),
           "provider": provider, "model": model_id, "model_key": price_key(model_id), "tier": tier,
           "input_tokens": usage.get("inputTokens", 0), "output_tokens": usage.get("outputTokens", 0),
           "cache_write_tokens": usage.get("cacheWriteInputTokens", 0),
           "cache_read_tokens": usage.get("cacheReadInputTokens", 0),
           "cost_usd": cost_usd(model_id, usage, tier=tier, provider=provider) if usage else 0.0,
           "latency_s": None if latency_s is None else round(latency_s, 2),
           "outcome": outcome, "error": (error or "")[:300] or None}
    _buffer.add(row)
    return row


class LedgerClient:
    """Wraps a Converse client (Bedrock runtime or AnthropicConverse) and records every
    `converse` call, including the ones that fail. Everything else passes through."""

    def __init__(self, inner, provider: str):
        self._inner, self._provider = inner, provider

    def converse(self, **kwargs):
        model_id = kwargs.get("modelId", "")
        t0 = time.monotonic()
        try:
            resp = self._inner.converse(**kwargs)
        except Exception as e:
            text = f"{type(e).__name__} {e}".lower()
            kind = "throttled" if "throttl" in text or "too many tokens" in text else "error"
            record(provider=self._provider, model_id=model_id, usage=None,
                   latency_s=time.monotonic() - t0, outcome=kind, error=f"{type(e).__name__}: {e}")
            raise
        record(provider=self._provider, model_id=model_id, usage=resp.get("usage"),
               latency_s=time.monotonic() - t0, outcome=resp.get("stopReason") or "ok")
        return resp

    def __getattr__(self, name):
        return getattr(self._inner, name)


# --- report ---------------------------------------------------------------------------


def read(store, since: str | None = None) -> list[dict]:
    rows = []
    for key in store.list(f"{PREFIX}/"):
        m = re.search(r"dt=(\d{4}-\d{2}-\d{2})/", key)
        if since and m and m.group(1) < since:
            continue
        rows += [json.loads(line) for line in store.get(key).decode().splitlines() if line.strip()]
    return rows


def summarise(rows: list[dict], by: list[str]) -> list[dict]:
    agg = defaultdict(lambda: defaultdict(float))
    for r in rows:
        k = tuple(r.get(b) or "" for b in by)
        a = agg[k]
        a["calls"] += 1
        a["failed"] += r.get("outcome") in ("error", "throttled")
        for f in ("input_tokens", "output_tokens", "cache_write_tokens", "cache_read_tokens"):
            a[f] += r.get(f, 0) or 0
        a["cost_usd"] += r.get("cost_usd") or 0
        if r.get("subject"):
            a.setdefault("subjects", set()).add(r["subject"])  # type: ignore[arg-type]
    out = []
    for k, a in sorted(agg.items(), key=lambda x: -x[1]["cost_usd"]):
        subjects = len(a.pop("subjects", ()) or ())
        row = dict(zip(by, k)) | {f: int(v) for f, v in a.items() if f != "cost_usd"}
        row["cost_usd"] = round(a["cost_usd"], 2)
        row["subjects"] = subjects
        row["usd_per_subject"] = round(a["cost_usd"] / subjects, 3) if subjects else None
        out.append(row)
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Summarise the call ledger.")
    p.add_argument("step", choices=["report"])
    p.add_argument("--run")
    p.add_argument("--job")
    p.add_argument("--since", help="first day to read, YYYY-MM-DD")
    p.add_argument("--by", default="job,provider,model_key,tier")
    p.add_argument("--store", default=os.environ.get("LAKE_URI"))
    a = p.parse_args(argv)
    from .store import store_from_uri
    store = store_from_uri(a.store or _root())
    rows = [r for r in read(store, a.since)
            if (not a.run or r.get("run") == a.run) and (not a.job or r.get("job") == a.job)]
    for row in summarise(rows, a.by.split(",")):
        print(json.dumps(row))
    print(json.dumps({"total_calls": len(rows), "total_cost_usd": round(sum(r.get("cost_usd") or 0 for r in rows), 2)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
