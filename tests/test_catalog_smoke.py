"""Smoke: the catalog questions are answered from the mapped tables, not from prose.

The evaluation set names which questions must hit a table. This runs those questions
through the same tools the agent calls, against a collection whose CSVs were uploaded
the way the lab stores them. No model is called.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fake_llm import FakeClient
from knowledge_store import layout
from knowledge_store.evals import score
from knowledge_store.pipeline import run
from knowledge_store.store import put_json
from knowledge_store.structured.query import describe
from knowledge_store.tools import gateway
from test_structured import _landing

ROOT = Path(__file__).resolve().parents[1]
SET = ROOT / "examples/evals/space-missions.yaml"


def _ask(root, spec: dict) -> dict:
    """One structured question, through the gateway tools."""
    tool = spec["tool"]
    if tool == "lookup_rows":
        out = gateway.call(root, "lookup_rows", {
            "collection": "missions", "type": spec["type"], "filters": spec.get("filters") or []})
        if out.get("error") or not out.get("rows"):
            return {"ok": False, "detail": out}
        if "names" in spec:
            got = [r["values"].get("name", {}).get("value") for r in out["rows"]]
            cells = [r["values"].get("name", {}).get("cell") for r in out["rows"]]
            return {"ok": sorted(got) == sorted(spec["names"]) and all(str(c).startswith("c:") for c in cells),
                    "got": got}
        expect = {k: str(v) for k, v in (spec.get("expect") or {}).items()}
        if out.get("total") != 1:
            return {"ok": False, "detail": out}
        vals = out["rows"][0]["values"]
        got = {k: str((vals.get(k) or {}).get("value")) for k in expect}
        cells = [(vals.get(k) or {}).get("cell") for k in expect]
        return {"ok": got == expect and all(c and str(c).startswith("c:") for c in cells), "got": got}
    if tool == "aggregate":
        out = gateway.call(root, "aggregate", {
            "collection": "missions", "metric": spec.get("metric") or "", "type": spec.get("type") or "",
            "op": spec.get("op") or "", "attribute": spec.get("attribute") or "",
            "filters": spec.get("filters") or []})
        fig, want = out.get("figure"), spec["figure"]
        return {"ok": "error" not in out and str(out.get("id", "")).startswith("m:") and (fig == want or str(fig) == str(want)),
                "got": fig, "detail": out.get("error")}
    return {"ok": False, "detail": f"unknown tool {tool}"}


@pytest.mark.parametrize("layout_name", ["nested", "flat"])
def test_catalog_questions_hit_the_tables(tmp_path, layout_name):
    root, lake = _landing(tmp_path, layout_name)
    put_json(lake, layout.CONFIG_SETTINGS, {"ontology_mode": "curated", "discovery_min_docs": 99})
    rounds = run.run(root, FakeClient, "fake")
    assert rounds["missions"][0]["bind"]["missing"] == [], rounds

    described = describe(lake)
    bound = {t["logical_table"]: t.get("snapshot") for t in described["types"]}
    assert bound.get("missions") and bound.get("launch_vehicles"), described

    catalog = [q for q in score.load(SET).questions if q.structured]
    assert len(catalog) >= 5
    for q in catalog:
        got = _ask(root, q.structured)
        assert got["ok"], f"{q.id} {q.question}: {got}"


def test_a_table_citation_counts_as_the_catalog_source():
    q = next(q for q in score.load(SET).questions if q.id == "u01")
    hit = score.score(q, {"answer": "The catalog gives Juno a sample cost of 1100.",
                          "sources": [{"name": "missions", "kind": "cell", "title": "sample_cost_million_usd = 1100"}]})
    assert hit["correct"] and hit["source_hit"] is True
    missed = score.score(q, {"answer": "1100", "sources": [{"name": "outer-planets/juno.json"}]})
    assert missed["correct"] and missed["source_hit"] is False
