"""A run against a baseline: what changed, and whether a release may go ahead.

The gate is deterministic. A release fails it when a question the baseline got right is now
wrong, when accuracy falls by more than the allowed drop, or when false answers or unsupported
claims rise. Each rule can be loosened per set, and every failure is named, so a person can
accept a regression on purpose by moving the baseline rather than by turning the gate off.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Rules:
    max_accuracy_drop: float = 0.0          # absolute, e.g. 0.05
    allow_regressions: int = 0              # questions right in the baseline and wrong now
    max_false_answer_rise: int = 0
    max_unsupported_rise: int = 0


@dataclass
class Gate:
    passed: bool
    failures: list[str] = field(default_factory=list)
    regressions: list[str] = field(default_factory=list)
    fixed: list[str] = field(default_factory=list)
    deltas: dict = field(default_factory=dict)


def _all(run: dict) -> dict:
    return run["summary"]["all"]


def compare(run: dict, baseline: dict, rules: Rules | None = None) -> Gate:
    rules = rules or Rules()
    now = {r["id"]: r for r in run["rows"]}
    then = {r["id"]: r for r in baseline["rows"]}
    shared = sorted(set(now) & set(then))
    regressions = [i for i in shared if then[i]["correct"] and not now[i]["correct"]]
    fixed = [i for i in shared if not then[i]["correct"] and now[i]["correct"]]
    a, b = _all(run), _all(baseline)
    acc_now = sum(now[i]["correct"] for i in shared) / len(shared) if shared else 0.0
    acc_then = sum(then[i]["correct"] for i in shared) / len(shared) if shared else 0.0
    deltas = {"accuracy": round(acc_now - acc_then, 3),
              "false_answers": (a.get("false_answers") or 0) - (b.get("false_answers") or 0),
              "false_abstentions": (a.get("false_abstentions") or 0) - (b.get("false_abstentions") or 0)}
    if a.get("unsupported_claims") is not None and b.get("unsupported_claims") is not None:
        deltas["unsupported_claims"] = a["unsupported_claims"] - b["unsupported_claims"]
    failures = []
    if len(regressions) > rules.allow_regressions:
        failures.append(f"{len(regressions)} question(s) right in the baseline are wrong now: {', '.join(regressions)}")
    if -deltas["accuracy"] > rules.max_accuracy_drop + 1e-9:
        failures.append(f"accuracy fell by {-deltas['accuracy']:.3f} on the {len(shared)} shared questions")
    if deltas["false_answers"] > rules.max_false_answer_rise:
        failures.append(f"false answers rose by {deltas['false_answers']}")
    if deltas.get("unsupported_claims", 0) > rules.max_unsupported_rise:
        failures.append(f"unsupported claims rose by {deltas['unsupported_claims']}")
    missing = sorted(set(then) - set(now))
    if missing:
        failures.append(f"{len(missing)} baseline question(s) were not run: {', '.join(missing)}")
    return Gate(passed=not failures, failures=failures, regressions=regressions, fixed=fixed, deltas=deltas)
