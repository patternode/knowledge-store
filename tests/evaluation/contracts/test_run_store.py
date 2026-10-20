"""The RunStore port: a saved run can be found again, a baseline is None until kept, and keeping
replaces it. Run against DirRunStore and LakeRunStore over a local Store."""

from __future__ import annotations

import json

import pytest

from knowledge_store.evaluation import DirRunStore, LakeRunStore
from knowledge_store.platform_services.adapters.store import LocalStore

RUN = {"set": "space", "rows": [{"id": "a", "correct": True}], "when": "2026-10-20T09:30:00+00:00"}


@pytest.fixture(params=["dir", "lake"])
def store(request, tmp_path):
    if request.param == "dir":
        return DirRunStore(tmp_path / "runs")
    return LakeRunStore(LocalStore(tmp_path / "lake"))


def test_no_baseline_until_one_is_kept(store):
    assert store.baseline("space") is None


def test_a_kept_baseline_reads_back(store):
    store.keep_as_baseline("space", RUN)
    assert store.baseline("space") == RUN


def test_keeping_again_replaces_the_baseline(store):
    store.keep_as_baseline("space", RUN)
    store.keep_as_baseline("space", {**RUN, "rows": []})
    assert store.baseline("space")["rows"] == []


def test_baselines_are_per_set(store):
    store.keep_as_baseline("space", RUN)
    assert store.baseline("holmes") is None


def test_saving_returns_where_the_run_went(store):
    where = store.save("space-20261020", RUN, "# report\n")
    assert isinstance(where, str) and "space-20261020" in where


def test_saving_a_run_does_not_make_it_the_baseline(store):
    store.save("space-1", RUN, "r")
    assert store.baseline("space") is None


def test_values_json_cannot_hold_are_written_as_text(store):
    import datetime as dt
    store.keep_as_baseline("space", {**RUN, "at": dt.date(2026, 10, 20)})
    assert store.baseline("space")["at"] == "2026-10-20"


# --- where each adapter puts things ---------------------------------------------------------------

def test_a_folder_store_writes_the_results_and_the_report(tmp_path):
    where = DirRunStore(tmp_path).save("r1", RUN, "# report\n")
    assert json.loads((tmp_path / "r1" / "results.json").read_text()) == RUN
    assert (tmp_path / "r1" / "report.md").read_text() == "# report\n" and where == str(tmp_path / "r1")
    DirRunStore(tmp_path).keep_as_baseline("space", RUN)
    assert (tmp_path / "baselines" / "space.json").exists()


def test_a_lake_store_keeps_runs_under_private(tmp_path):
    lake = LocalStore(tmp_path)
    LakeRunStore(lake).save("r1", RUN, "# report\n")
    LakeRunStore(lake).keep_as_baseline("space", RUN)
    keys = sorted(lake.list("private/evals/"))
    assert keys == ["private/evals/baselines/space.json", "private/evals/r1/report.md", "private/evals/r1/results.json"]


def test_a_lake_store_takes_another_prefix(tmp_path):
    lake = LocalStore(tmp_path)
    LakeRunStore(lake, prefix="private/other/").keep_as_baseline("s", RUN)
    assert lake.exists("private/other/baselines/s.json")
