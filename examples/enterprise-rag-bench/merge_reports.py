"""Merge chunked evaluate runs into one results.json and report.md, and tabulate arms side by side.

    merge_reports.py merge <out_dir> <chunk_dir>...      each chunk dir holds enterprise-rag-bench-*/results.json
    merge_reports.py compare <name=results.json>...       one column per arm
"""
import glob, json, pathlib, sys
from knowledge_store.evaluation.domain import score as scoring
from knowledge_store.evaluation.adapters.report import report

def latest(d):
    runs = sorted(glob.glob(str(pathlib.Path(d) / "enterprise-rag-bench-*" / "results.json")))
    return json.load(open(runs[-1])) if runs else None

def merge(out, chunks):
    runs = [r for r in (latest(c) for c in chunks) if r]
    # one row per question: a later run of the same id replaces an earlier one, and an answer beats an error
    best = {}
    for r in sorted(runs, key=lambda r: r["when"]):
        res_by_id = {x["id"]: x for x in r["results"]}
        for row in r["rows"]:
            held = best.get(row["id"])
            if held is None or held[0].get("error") or not row.get("error"):
                best[row["id"]] = (row, res_by_id[row["id"]])
    rows = [v[0] for v in best.values()]
    results = [v[1] for v in best.values()]
    merged = {"set": runs[0]["set"], "collection": runs[0]["collection"], "when": max(r["when"] for r in runs),
              "summary": scoring.summarise(rows), "rows": sorted(rows, key=lambda x: x["id"]),
              "results": sorted(results, key=lambda x: x["id"]),
              "tokens": {k: sum(r["tokens"].get(k, 0) for r in runs) for k in runs[0]["tokens"]},
              "chunks": len(runs)}
    d = pathlib.Path(out); d.mkdir(parents=True, exist_ok=True)
    (d / "results.json").write_text(json.dumps(merged, indent=1, default=str))
    (d / "report.md").write_text(report(merged))
    print(f"merged {len(rows)} rows from {len(runs)} chunks into {d}")
    print((d / "report.md").read_text()[:1500])

def mean(xs):
    xs = [x for x in xs if isinstance(x, (int, float))]
    return round(sum(xs) / len(xs), 3) if xs else None

def compare(arms):
    data = {}
    for a in arms:
        name, path = a.split("=", 1)
        data[name] = json.load(open(path))
    def metric(rows, key):
        return mean([(r.get("grade") or {}).get("metrics", {}).get(key, {}).get("score") for r in rows])
    lines = ["| Measure | " + " | ".join(data) + " |", "|---|" + "---|" * len(data)]
    def add(label, f):
        lines.append(f"| {label} | " + " | ".join(str(f(d)) for d in data.values()) + " |")
    add("Questions", lambda d: len(d["rows"]))
    add("Correct (score)", lambda d: f"{sum(r['correct'] for r in d['rows'])} ({mean([r['score'] for r in d['rows']])})")
    add("Grader pass", lambda d: sum((r.get("grade") or {}).get("verdict") == "pass" for r in d["rows"]))
    add("Correctness (G-Eval mean)", lambda d: metric(d["rows"], "correctness"))
    add("Completeness (facts stated, mean)", lambda d: metric(d["rows"], "completeness"))
    add("Faithfulness (mean)", lambda d: metric(d["rows"], "faithfulness"))
    add("Cited an expected source", lambda d: mean([r["source_hit"] for r in d["rows"] if r.get("source_hit") is not None]))
    add("False abstentions", lambda d: sum(bool(r.get("false_abstention")) for r in d["rows"]))
    add("False answers", lambda d: sum(bool(r.get("false_answer")) for r in d["rows"]))
    add("Errors", lambda d: sum(bool(r.get("error")) for r in d["rows"]))
    for kind in ("lookup", "multi-hop", "list", "unanswerable"):
        add(f"Correct, {kind}", lambda d, k=kind: f"{sum(r['correct'] for r in d['rows'] if r['kind'] == k)} of {sum(r['kind'] == k for r in d['rows'])}")
    add("Tokens in, out", lambda d: f"{d['tokens'].get('inputTokens')}, {d['tokens'].get('outputTokens')}")
    print("\n".join(lines))

if __name__ == "__main__":
    {"merge": lambda: merge(sys.argv[2], sys.argv[3:]), "compare": lambda: compare(sys.argv[2:])}[sys.argv[1]]()
