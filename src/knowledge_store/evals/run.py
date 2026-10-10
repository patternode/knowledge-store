"""Run an evaluation set against the agent and write a report.

    python -m knowledge_store.evals <set.yaml> --lake <uri>               the agent in-process, on that lake
    python -m knowledge_store.evals <set.yaml> --api <url> [--token-env]  the deployed chat API, as a person
    ... --out build/eval/<name>      where the report goes (report.md, results.json)
    ... --only q01,q07               a subset
    ... --yes                        agree to the model spend; without it, the estimate is printed and nothing runs

In-process runs the same agent code against the lake with the tools in-process (agent/app.py
answer_locally): the graph from Neptune when NEPTUNE_ENDPOINT is set, else from the projection;
passages from the Knowledge Base when KNOWLEDGE_BASE_ID is set, else by keyword. It calls Bedrock
(AGENT_MODEL_ID) with your AWS credentials. Against the API, each question counts against that
person's daily quota, and the token is a Cognito access token for them (from --token-env).

Every question is a model run of several calls, so a run costs money: ESTIMATE_USD_PER_QUESTION
is a planning figure for a Sonnet-class model (about 60,000 input and 3,000 output tokens a
question); the report records the tokens actually used when the agent reports them.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

from . import score

ESTIMATE_USD_PER_QUESTION = 0.25


def local_target(lake_uri: str, collection: str, model_id: str | None):
    from ..agent.app import answer_locally
    from ..store import store_from_uri
    root = store_from_uri(lake_uri)

    def ask(q: score.Question) -> dict:
        return answer_locally(root, collection, q.question, private=q.private, model_id=model_id)
    return ask


def api_target(url: str, token: str, collection: str, timeout_s: int = 300):
    base = url.rstrip("/")

    def call(method: str, path: str, body: dict | None = None) -> dict:
        req = urllib.request.Request(base + path, method=method, data=json.dumps(body).encode() if body else None,
                                     headers={"Authorization": f"Bearer {token}", "content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())

    def ask(q: score.Question) -> dict:
        job = call("POST", f"/api/chat?c={collection}", {"question": q.question})
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            time.sleep(3)
            r = call("GET", f"/api/chat?c={collection}&id={job['id']}")
            if r.get("status") == "done":
                return r
            if r.get("status") == "failed":
                return {"error": r.get("error") or "failed", "abstained": True}
        return {"error": "timed out", "abstained": True}
    return ask


def run(evalset: score.EvalSet, ask, only: list[str] | None = None, progress=print) -> dict:
    rows, results = [], []
    for q in evalset.questions:
        if only and q.id not in only:
            continue
        started = time.monotonic()
        try:
            res = ask(q)
        except Exception as e:  # one failed question scores zero; the run goes on
            res = {"error": f"{type(e).__name__}: {str(e)[:300]}", "abstained": True}
        row = {**score.score(q, res), "seconds": round(time.monotonic() - started, 1),
               "usage": res.get("usage"), "tool_calls": len(res.get("tool_calls") or [])}
        rows.append(row)
        results.append({"id": q.id, "question": q.question, "expected": q.expected, "result": res})
        progress(f"{q.id} {q.kind:<12} {'PASS' if row['correct'] else 'FAIL'} score={row['score']} "
                 f"grounded={row['grounded']} {row['seconds']}s")
    return {"set": evalset.name, "collection": evalset.collection,
            "when": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
            "summary": score.summarise(rows), "rows": rows, "results": results,
            "tokens": tokens(rows)}


def tokens(rows: list[dict]) -> dict:
    total = {"inputTokens": 0, "outputTokens": 0}
    for r in rows:
        for k in total:
            total[k] += int((r.get("usage") or {}).get(k) or 0)
    return total


def report(out: dict) -> str:
    s = out["summary"]["all"]
    lines = [f"# Evaluation: {out['set']} ({out['collection']})", "", f"Run {out['when']}.", "",
             "| Measure | Value |", "|---|---|",
             f"| Correct | {s['correct']} of {s['questions']} ({s['accuracy']}) |",
             f"| Mean score | {s['mean_score']} |",
             f"| Grounded (claims that passed the citation checks) | {s['grounded']} |",
             f"| Cited an expected source | {s['source_hit_rate']} |",
             f"| False negatives: abstained on an answerable question | {s['false_abstentions']} |",
             f"| False positives: answered an unanswerable question | {s['missed_abstentions']} |",
             f"| Errors | {s['errors']} |",
             f"| Tokens (input, output) | {out['tokens']['inputTokens']}, {out['tokens']['outputTokens']} |",
             "", "## By kind", "", "| Kind | Questions | Correct | Mean score | Grounded |", "|---|---|---|---|---|"]
    for k, b in out["summary"].items():
        if k != "all":
            lines.append(f"| {k} | {b['questions']} | {b['correct']} | {b['mean_score']} | {b['grounded']} |")
    lines += ["", "## Questions", "", "| Id | Kind | Correct | Score | Grounded | Source | Missing or forbidden |",
              "|---|---|---|---|---|---|---|"]
    for r in out["rows"]:
        why = ", ".join(r.get("missing") or []) + (f" (said {', '.join(r['forbidden'])})" if r.get("forbidden") else "")
        if r.get("error"):
            why = f"error: {r['error'][:80]}"
        lines.append(f"| {r['id']} | {r['kind']} | {'yes' if r['correct'] else 'no'} | {r['score']} | {r['grounded']} | "
                     f"{'' if r['source_hit'] is None else ('yes' if r['source_hit'] else 'no')} | {why} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m knowledge_store.evals", description=__doc__.split("\n\n")[0])
    ap.add_argument("set", type=Path)
    ap.add_argument("--lake", default=os.environ.get("LAKE_URI"))
    ap.add_argument("--api", help="the deployed chat API's base URL (the portal URL)")
    ap.add_argument("--token-env", default="KS_TOKEN", help="environment variable holding the caller's access token")
    ap.add_argument("--model", default=os.environ.get("AGENT_MODEL_ID"))
    ap.add_argument("--out", type=Path)
    ap.add_argument("--only")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args(argv)
    ev = score.load(a.set)
    only = a.only.split(",") if a.only else None
    n = len([q for q in ev.questions if not only or q.id in only])
    if not a.yes:
        print(f"{n} questions, each a model run of several calls: about {n * ESTIMATE_USD_PER_QUESTION:.2f} USD "
              f"at {ESTIMATE_USD_PER_QUESTION} USD a question. Re-run with --yes to go ahead.")
        return 2
    if a.api:
        token = os.environ.get(a.token_env)
        if not token:
            print(f"set {a.token_env} to an access token for the person to ask as")
            return 2
        ask = api_target(a.api, token, ev.collection)
    else:
        if not a.lake:
            print("give --lake (or set LAKE_URI), or --api")
            return 2
        if not a.model:
            print("give --model (or set AGENT_MODEL_ID)")
            return 2
        ask = local_target(a.lake, ev.collection, a.model)
    out = run(ev, ask, only)
    dest = a.out or Path("build/eval") / f"{ev.name}-{out['when'][:19].replace(':', '')}"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "results.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    (dest / "report.md").write_text(report(out), encoding="utf-8")
    print(report(out))
    print(f"written to {dest}")
    return 0 if out["summary"]["all"]["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
