"""The release gate (evaluation/slices/gate.py) through an in-memory RunStore: a baseline moves only
on purpose, and never on a failing run."""

from __future__ import annotations

from knowledge_store.evaluation import Rules, gate
from knowledge_store.evaluation.domain.score import summarise


class MemoryRunStore:
    def __init__(self, baselines=None):
        self.baselines, self.saved = dict(baselines or {}), {}

    def save(self, name, run, report):
        self.saved[name] = (run, report)
        return f"memory://{name}"

    def baseline(self, set_name):
        return self.baselines.get(set_name)

    def keep_as_baseline(self, set_name, run):
        self.baselines[set_name] = run


def run_of(correct):
    rows = [{"id": i, "kind": "lookup", "correct": c, "score": float(c), "grounded": None, "source_hit": None}
            for i, c in correct.items()]
    return {"set": "s", "rows": rows, "summary": summarise(rows)}


def test_without_a_baseline_there_is_no_verdict_and_nothing_is_kept():
    store = MemoryRunStore()
    assert gate(run_of({"a": True}), store) is None and store.baselines == {}


def test_without_a_baseline_keep_makes_the_run_the_first_baseline():
    store, first = MemoryRunStore(), run_of({"a": True})
    assert gate(first, store, keep=True) is None and store.baselines["s"] is first


def test_a_passing_run_is_judged_against_the_baseline_and_not_kept_by_default():
    base = run_of({"a": True})
    store = MemoryRunStore({"s": base})
    g = gate(run_of({"a": True}), store)
    assert g.passed and store.baselines["s"] is base


def test_a_passing_run_replaces_the_baseline_when_asked():
    store, better = MemoryRunStore({"s": run_of({"a": False})}), run_of({"a": True})
    g = gate(better, store, keep=True)
    assert g.passed and g.fixed == ["a"] and store.baselines["s"] is better


def test_a_failing_run_never_becomes_the_baseline():
    base = run_of({"a": True})
    store = MemoryRunStore({"s": base})
    g = gate(run_of({"a": False}), store, keep=True)
    assert not g.passed and g.regressions == ["a"] and store.baselines["s"] is base


def test_rules_are_passed_through():
    store = MemoryRunStore({"s": run_of({"a": True, "b": True})})
    assert gate(run_of({"a": True, "b": False}), store, Rules(allow_regressions=1, max_accuracy_drop=0.5)).passed


def test_each_set_has_its_own_baseline():
    store = MemoryRunStore({"other": run_of({"a": True})})
    assert gate(run_of({"a": False}), store) is None
