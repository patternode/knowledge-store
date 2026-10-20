"""Compare a run with the set's baseline and decide whether a release may go ahead."""

from __future__ import annotations

from knowledge_store.evaluation.domain.compare import Gate, Rules, compare
from knowledge_store.evaluation.ports import RunStore


def gate(run: dict, store: RunStore, rules: Rules | None = None, *, keep: bool = False) -> Gate | None:
    """None when the set has no baseline yet. keep: when the gate passes, the run becomes the
    baseline (a person moves it on purpose, never the gate on failure)."""
    base = store.baseline(run["set"])
    if base is None:
        if keep:
            store.keep_as_baseline(run["set"], run)
        return None
    result = compare(run, base, rules)
    if keep and result.passed:
        store.keep_as_baseline(run["set"], run)
    return result
