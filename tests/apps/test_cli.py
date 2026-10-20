"""The command line (apps/cli.py) over a local lake: one end-to-end sweep with a fake model, the
read-only commands, and its refusals."""

from __future__ import annotations

import json

import pytest

from fake_llm import FakeClient
from knowledge_store.apps import cli
from knowledge_store.platform_services.adapters.store import LocalStore
from knowledge_store.platform_services.domain import layout
from knowledge_store.platform_services.ports import put_json
from knowledge_store.platform_services.slices import collections
from test_lifecycle import DOCS, PROFILE


@pytest.fixture
def lake(tmp_path, monkeypatch):
    root = LocalStore(tmp_path / "lake")
    put_json(root, collections.CONFIG, [{"id": "m"}])
    for n, b in DOCS.items():
        root.put(f"landing/m/{n}", b.encode())
    lk = collections.scoped(root, "m")
    put_json(lk, layout.CONFIG_SOURCES, [{"name": "docs", "type": "s3_landing", "options": {"prefix": "landing/m/"}}])
    put_json(lk, layout.CONFIG_SETTINGS, {"ontology_mode": "auto", "discovery_min_docs": 3, "discovery_resamples": 1})
    put_json(lk, layout.CONFIG_PROFILE, PROFILE.to_dict())
    monkeypatch.setattr(cli, "_client", FakeClient)
    monkeypatch.delenv("LAKE_URI", raising=False)
    monkeypatch.delenv("COLLECTION", raising=False)
    return str(tmp_path / "lake")


def out_of(capsys):
    return json.loads(capsys.readouterr().out)


def test_status_before_any_run_is_never_run(lake, capsys):
    assert cli.main(["--lake", lake, "-c", "m", "status"]) == 0
    assert out_of(capsys) == {"stage": "never_run"}


def test_a_run_sweeps_the_collection_to_ready(lake, capsys):
    assert cli.main(["--lake", lake, "--model", "fake", "run"]) == 0
    rounds = out_of(capsys)["m"]
    assert rounds and rounds[0]["ingest"]["docs"]["stored"] == len(DOCS)
    assert cli.main(["--lake", lake, "-c", "m", "status"]) == 0
    assert out_of(capsys)["stage"] == "ready"
    assert cli.main(["--lake", lake, "collections"]) == 0
    assert out_of(capsys) == [{"id": "m", "status": "ready"}]
    assert cli.main(["--lake", lake, "-c", "m", "ontology", "active"]) == 0
    assert capsys.readouterr().out.strip() == "0.1.0"


def test_the_ingest_step_runs_alone(lake, capsys):
    assert cli.main(["--lake", lake, "-c", "m", "ingest"]) == 0
    assert out_of(capsys)["docs"]["stored"] == len(DOCS)


def test_the_steps_run_one_at_a_time(lake, capsys):
    from knowledge_store.ingestion.adapters.registry import ingest_source
    from knowledge_store.platform_services.slices.config import load_sources
    lk = collections.scoped(LocalStore(lake), "m")
    for source in load_sources(lk):
        ingest_source(lk, source)
    assert cli.main(["--lake", lake, "-c", "m", "refine"]) == 0
    assert out_of(capsys)["refined"] == len(DOCS)
    assert cli.main(["--lake", lake, "-c", "m", "ontology", "versions"]) == 0
    assert out_of(capsys) == []


def test_without_a_lake_it_refuses(monkeypatch, capsys):
    monkeypatch.delenv("LAKE_URI", raising=False)
    with pytest.raises(SystemExit) as e:
        cli.main(["status"])
    assert e.value.code == 2 and "--lake or LAKE_URI is required" in capsys.readouterr().err


def test_candidates_without_an_active_ontology_refuses(lake, capsys):
    with pytest.raises(SystemExit) as e:
        cli.main(["--lake", lake, "-c", "m", "candidates"])
    assert e.value.code == 2 and "no active ontology" in capsys.readouterr().err


def test_an_unknown_command_refuses(lake):
    with pytest.raises(SystemExit):
        cli.main(["--lake", lake, "explode"])
