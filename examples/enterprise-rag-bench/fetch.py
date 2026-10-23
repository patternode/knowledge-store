"""Fetch a slice of EnterpriseRAG-Bench and write its questions as an evaluation set.

    python examples/enterprise-rag-bench/fetch.py [out_dir] [--distractors N] [--collection ID]
                                                            # default: examples/enterprise-rag-bench/data

EnterpriseRAG-Bench (Onyx, MIT licence, https://github.com/onyx-dot-app/EnterpriseRAG-Bench) is
about 512,000 generated documents of one invented company, Redwood Inference, across nine source
types (Confluence, Jira, Slack, Gmail, Google Drive, Linear, HubSpot, Fireflies, GitHub), and 500
questions with the documents that answer them. The whole corpus is 5 GB; this takes the documents
the questions cite (722 of them) and, for each, N others from the same folder (1 by default), so
retrieval and entity resolution have near neighbours to tell apart. Which neighbours is fixed by a
hash of their paths, so every run at the same commit fetches the same files.

It writes four things under out_dir:

    documents/<source>/...json     upload these to landing/<collection>/; each keeps its path in the benchmark
    reference/                     the company the corpus was generated from (people, projects,
                                   initiatives). Not for upload: what extraction should find, to check the graph against
    enterprise-rag-bench.yaml      the evaluation set, for python -m knowledge_store.apps.evaluate
    documents.jsonl                the slice's document ids and paths, one a line: the --answers-index
                                   for grading another system's answers, which cite the benchmark's ids

Files are fetched from one commit of the GitHub repository, one at a time, with a User-Agent that
says what this is. A file already on disk is not fetched again, so an interrupted run resumes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO = "onyx-dot-app/EnterpriseRAG-Bench"
COMMIT = "d36685e273713975ee20299bbf1ab64165575b3c"
RAW = f"https://raw.githubusercontent.com/{REPO}/{COMMIT}/"
UA = "knowledge-store-demo/0.1 (fetch of an EnterpriseRAG-Bench slice for an evaluation corpus)"
REFERENCE = ["company_overview.md", "initiatives.md", "project_list.txt", "employee_directory.yaml"]

# The benchmark's question types, as this repository's kinds. high_level is left out: it has no
# gold documents, and its answers summarise the whole corpus, which a slice does not hold.
KINDS = {
    "basic": "lookup", "semantic": "lookup", "constrained": "lookup", "miscellaneous": "lookup",
    "conflicting_info": "lookup", "intra_document_reasoning": "multi-hop", "project_related": "multi-hop",
    "completeness": "list", "info_not_found": "unanswerable",
}


def selected(questions: list[dict]) -> list[dict]:
    return [q for q in questions if q["question_type"] in KINDS]


def gold_paths(questions: list[dict], index: dict[str, str]) -> list[str]:
    return sorted({index[d] for q in questions for d in q["expected_doc_ids"]})


def distractors(gold: list[str], paths: list[str], per_doc: int) -> list[str]:
    """per_doc documents from each gold document's folder that no question cites, chosen by a
    hash of the path so the choice does not depend on the order of the index."""
    if per_doc <= 0:
        return []
    by_dir: dict[str, list[str]] = {}
    for p in paths:
        by_dir.setdefault(posixpath.dirname(p), []).append(p)
    gold_set, out = set(gold), set()
    for g in gold:
        pool = sorted((p for p in by_dir.get(posixpath.dirname(g), []) if p not in gold_set and p not in out),
                      key=lambda p: hashlib.sha256(f"{g}|{p}".encode()).hexdigest())
        out.update(pool[:per_doc])
    return sorted(out)


def to_question(q: dict, index: dict[str, str]) -> dict:
    kind = KINDS[q["question_type"]]
    out = {"id": q["question_id"], "kind": kind, "question": q["question"]}
    context = {"question_type": q["question_type"], "answer_facts": q["answer_facts"]}
    if kind == "unanswerable":
        out["answerable"] = False
        out["note"] = "Not answerable from the full corpus, so not from this slice either."
    else:
        out["judged"] = True
        out["expected"] = q["gold_answer"]
        out["sources"] = sorted({index[d] for d in q["expected_doc_ids"]})
    out["context"] = context
    return out


def document_index(docs: list[str], index: dict[str, str]) -> list[dict]:
    """The fetched documents as {doc_id, path} rows, in path order."""
    ids = {path: doc_id for doc_id, path in index.items()}
    return [{"doc_id": ids[p], "path": p} for p in sorted(docs)]


def eval_set(questions: list[dict], index: dict[str, str], collection: str) -> dict:
    return {"name": "enterprise-rag-bench", "collection": collection,
            "questions": [to_question(q, index) for q in selected(questions)]}


def fetch(path: str) -> bytes:
    req = urllib.request.Request(RAW + urllib.parse.quote(path), headers={"User-Agent": UA})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except OSError:
            if attempt == 3:
                raise
            time.sleep(2 ** (attempt + 2))
    raise AssertionError("unreachable")


def fetch_to(path: str, dest: Path) -> bool:
    if dest.exists():
        return False
    data = fetch(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out", nargs="?", default=str(Path(__file__).parent / "data"))
    ap.add_argument("--distractors", type=int, default=1, help="documents per gold document from its folder")
    ap.add_argument("--collection", default="redwood")
    args = ap.parse_args()
    out = Path(args.out)

    import yaml

    for name in REFERENCE:
        fetch_to(f"generated_data/{name}", out / "reference" / name)
    questions = [json.loads(line) for line in fetch("questions.jsonl").decode("utf-8").splitlines() if line.strip()]
    print(f"index of every document ({COMMIT[:7]}), about 60 MB ...")
    index: dict[str, str] = json.loads(fetch("generated_data/uuid_index.json"))

    chosen = selected(questions)
    gold = gold_paths(chosen, index)
    extra = distractors(gold, list(index.values()), args.distractors)
    docs = gold + extra
    print(f"{len(chosen)} questions, {len(gold)} gold documents, {len(extra)} distractors")
    fetched = 0
    for n, p in enumerate(docs, 1):
        if fetch_to(f"generated_data/sources/{p}", out / "documents" / p):
            fetched += 1
            time.sleep(0.05)
        if n % 100 == 0 or n == len(docs):
            print(f"{n}/{len(docs)} documents ({fetched} fetched)")

    (out / "documents.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in document_index(docs, index)), encoding="utf-8")
    (out / "enterprise-rag-bench.yaml").write_text(
        f"# Generated by examples/enterprise-rag-bench/fetch.py from {REPO}@{COMMIT[:7]} (MIT licence).\n"
        + yaml.safe_dump(eval_set(questions, index, args.collection), sort_keys=False, allow_unicode=True, width=120),
        encoding="utf-8")
    print(f"wrote {out / 'enterprise-rag-bench.yaml'}")


if __name__ == "__main__":
    sys.exit(main())
