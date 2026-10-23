"""A run as Markdown: the measures, the gate, and every question."""

from __future__ import annotations


def _ci(v) -> str:
    return f"{v[0]} to {v[1]}" if v else ""


def report(out: dict, gate=None) -> str:
    s = out["summary"]["all"]
    lines = [f"# Evaluation: {out['set']} ({out['collection']})", "", f"Run {out['when']}.", "",
             "| Measure | Value |", "|---|---|",
             f"| Correct | {s['correct']} of {s['questions']} ({s['accuracy']}; 95% interval {_ci(s.get('accuracy_ci95'))}) |",
             f"| Mean score | {s['mean_score']} |",
             f"| Grounded (claims that passed the agent's own citation checks) | {s['grounded']} |",
             f"| Cited an expected source | {s['source_hit_rate']} |",
             f"| Citation precision, recall | {s.get('citation_precision')}, {s.get('citation_recall')} |",
             f"| False answers: stated a fact for an unanswerable question | {s['false_answers']} |",
             f"| False abstentions: declined an answerable question | {s['false_abstentions']} |"]
    if s.get("unsupported_claims") is not None:
        lines.append(f"| Unsupported claims: rejected by the claim verifier | {s['unsupported_claims']} of {s['claims_verified']} |")
    fam = out["summary"].get("families")
    if fam:
        lines.append(f"| Paraphrase families answered alike | {fam['consistent']} of {fam['families']} |")
    lines += [f"| Errors | {s['errors']} |",
              f"| Tokens (input, output) | {out['tokens']['inputTokens']}, {out['tokens']['outputTokens']} |"]
    if gate is not None:
        lines += ["", "## Release gate", "", "Passed." if gate.passed else "Failed:", ""]
        lines += [f"- {f}" for f in gate.failures]
        if gate.fixed:
            lines.append(f"- Now right, wrong in the baseline: {', '.join(gate.fixed)}")
    lines += ["", "## By kind", "", "| Kind | Questions | Correct | Mean score | Grounded |", "|---|---|---|---|---|"]
    for k, b in out["summary"].items():
        if k not in ("all", "families", "graded"):
            lines.append(f"| {k} | {b['questions']} | {b['correct']} | {b['mean_score']} | {b['grounded']} |")
    graded = out["summary"].get("graded")
    if graded:
        lines += ["", "## Grader", "", "A model's judgement, reported beside the score and never folded into it.", "",
                  "| Verdict | Questions |", "|---|---|"]
        lines += [f"| {v} | {n} |" for v, n in graded.items()]
    head = "| Id | Kind | Correct | Score | Grounded | Unsupported | Source | Missing or forbidden |"
    lines += ["", "## Questions", "", head + (" Grade |" if graded else ""), "|---" * (9 if graded else 8) + "|"]
    for r in out["rows"]:
        why = ", ".join(r.get("missing") or []) + (f" (said {', '.join(r['forbidden'])})" if r.get("forbidden") else "")
        if r.get("false_answer"):
            why = (why + "; " if why else "") + "false answer"
        failed = [k for k, v in (r.get("truth") or {}).items() if v.get("ok") is False]
        if failed:
            why = (why + "; " if why else "") + "truth: " + ", ".join(f"{k} ({r['truth'][k].get('detail', '')})" for k in failed)
        if r.get("error"):
            why = f"error: {r['error'][:80]}"
        unsup = "" if r.get("unsupported") is None else str(r["unsupported"])
        grade = f" {(r.get('grade') or {}).get('verdict', '')} |" if graded else ""
        lines.append(f"| {r['id']} | {r['kind']} | {'yes' if r['correct'] else 'no'} | {r['score']} | {r['grounded']} | {unsup} | "
                     f"{'' if r['source_hit'] is None else ('yes' if r['source_hit'] else 'no')} | {why} |{grade}")
    return "\n".join(lines) + "\n"
