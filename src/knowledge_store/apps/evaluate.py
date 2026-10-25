"""Run an evaluation set against the agent and write a report.

    python -m knowledge_store.apps.evaluate <set.yaml> --lake <uri>               the agent in process, on that lake
    python -m knowledge_store.apps.evaluate <set.yaml> --api <url> [--token-env]  the deployed chat API, as a person
    python -m knowledge_store.apps.evaluate <set.yaml> --answers <file.jsonl>     another system's answers, scored and
                                    graded alike (one JSON object a line: question_id, answer, document_ids;
                                    --answers-index maps its document ids to the set's source names and
                                    --documents is the folder their text is read from)
    ... --out build/eval            where runs and baselines are kept (a folder, or s3://bucket for the lake's private/evals)
    ... --only q01,q07              a subset
    ... --verifier lexical|hhem|guardrail|none
                                    check every claim against what it cites (default lexical)
    ... --runner plain|deepeval     DeepEval records the run as a test run under --out (the evals extra)
    ... --grader none|deepeval      a model's judgement of correctness and faithfulness, beside the score
    ... --judge-model ID            the grader's model (default JUDGE_MODEL_ID, else --model)
    ... --upload-to-confident       let DeepEval send the run to Confident AI, outside the account
    ... --gate [--keep-baseline]    compare with the set's baseline and fail on a regression
    ... --max-tokens N              stop before a question once N tokens are spent
    ... --yes                       agree to the model spend; without it, the estimate is printed and nothing runs

Every question is a model run of several calls, so a run costs money: ESTIMATE_USD_PER_QUESTION
is a planning figure for a Sonnet-class model (about 60,000 input and 3,000 output tokens a
question); the report records the tokens actually used when the agent reports them. The grader
adds ESTIMATE_USD_PER_GRADE a question (a G-Eval call and four faithfulness calls); its calls are
in the call ledger.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from knowledge_store.evaluation import (DirRunStore, FileAnswerer, HttpAnswerer, InProcessAnswerer, LakeRunStore,
                                        LexicalVerifier, Rules, gate, load_answer_index, load_set, report, run)

ESTIMATE_USD_PER_QUESTION = 0.25
ESTIMATE_USD_PER_GRADE = 0.05


def verifier_for(name: str):
    if name == "none":
        return None
    if name == "hhem":
        from knowledge_store.evaluation import HhemVerifier
        return HhemVerifier()
    if name == "guardrail":
        from knowledge_store.answering import Guardrail
        g = Guardrail.from_env()
        if g is None:
            raise SystemExit("--verifier guardrail needs GUARDRAIL_ID")
        return g
    return LexicalVerifier()


def store_for(out: str):
    if out.startswith("s3://"):
        from knowledge_store.platform_services import store_from_uri
        return LakeRunStore(store_from_uri(out))
    return DirRunStore(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m knowledge_store.apps.evaluate", description=__doc__.split("\n\n")[0])
    ap.add_argument("set", type=Path)
    ap.add_argument("--lake", default=os.environ.get("LAKE_URI"))
    ap.add_argument("--api", help="the deployed chat API's base URL (the portal URL)")
    ap.add_argument("--answers", help="another system's answers, one JSON object a line")
    ap.add_argument("--answers-index", help="its document ids to the set's source names (JSON object or lines)")
    ap.add_argument("--documents", help="the folder the cited documents are read from, for the grader")
    ap.add_argument("--token-env", default="KS_TOKEN", help="environment variable holding the caller's access token")
    ap.add_argument("--model", default=os.environ.get("AGENT_MODEL_ID"))
    ap.add_argument("--out", default="build/eval")
    ap.add_argument("--only")
    ap.add_argument("--tools", default="all", choices=["all", "passages"],
                    help="in process: every tool (the graph, the tables, the passages), or passage search alone")
    ap.add_argument("--verifier", default="lexical", choices=["lexical", "hhem", "guardrail", "none"])
    ap.add_argument("--runner", default="plain", choices=["plain", "deepeval"])
    ap.add_argument("--grader", default="none", choices=["none", "deepeval"])
    ap.add_argument("--judge-model", default=os.environ.get("JUDGE_MODEL_ID"))
    ap.add_argument("--upload-to-confident", action="store_true")
    ap.add_argument("--gate", action="store_true")
    ap.add_argument("--keep-baseline", action="store_true")
    ap.add_argument("--max-accuracy-drop", type=float, default=0.0)
    ap.add_argument("--max-tokens", type=int)
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args(argv)
    ev = load_set(a.set)
    only = a.only.split(",") if a.only else None
    n = len([q for q in ev.questions if not only or q.id in only])
    per = (0 if a.answers else ESTIMATE_USD_PER_QUESTION) + (ESTIMATE_USD_PER_GRADE if a.grader != "none" else 0)
    if not a.yes:
        print(f"{n} questions, each a model run of several calls: about {n * per:.2f} USD "
              f"at {per} USD a question. Re-run with --yes to go ahead.")
        return 2
    judge_model = a.judge_model or a.model
    if a.grader == "deepeval" and not judge_model:
        print("give --judge-model (or set JUDGE_MODEL_ID) for the grader")
        return 2
    if a.answers:
        index = load_answer_index(a.answers_index) if a.answers_index else None
        ask = FileAnswerer(a.answers, index=index, documents=a.documents)
    elif a.api:
        token = os.environ.get(a.token_env)
        if not token:
            print(f"set {a.token_env} to an access token for the person to ask as")
            return 2
        ask = HttpAnswerer(a.api, token, ev.collection)
    else:
        if not a.lake:
            print("give --lake (or set LAKE_URI), or --api")
            return 2
        if not a.model:
            print("give --model (or set AGENT_MODEL_ID)")
            return 2
        ask = InProcessAnswerer(a.lake, ev.collection, a.model, toolset=a.tools)
    store = store_for(a.out)
    runner = grader = None
    if a.runner == "deepeval":
        from knowledge_store.evaluation import DeepEvalRunner
        local = Path("build/eval") if a.out.startswith("s3://") else Path(a.out)  # DeepEval writes to a folder
        runner = DeepEvalRunner(str(local / "deepeval"), identifier=ev.name, upload=a.upload_to_confident)
    if a.grader == "deepeval":
        from knowledge_store.evaluation import DeepEvalGrader
        grader = DeepEvalGrader(judge_model)
    out = run(ev, ask, only=only, verifier=verifier_for(a.verifier), grader=grader, runner=runner,
              max_tokens=a.max_tokens)
    result = gate(out, store, Rules(max_accuracy_drop=a.max_accuracy_drop), keep=a.keep_baseline) if a.gate else None
    text = report(out, result)
    where = store.save(f"{ev.name}-{out['when'][:19].replace(':', '')}", out, text)
    print(text)
    print(f"written to {where}")
    if result is not None and not result.passed:
        return 3
    return 0 if out["summary"]["all"]["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
