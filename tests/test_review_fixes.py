"""Regressions for the PR #162 review: the stack's modules are all in git, the portal's role covers
collection prefixes, and private-scope text never reaches a public caller."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

from fake_llm import FakeClient
from knowledge_store import collections, layout
from knowledge_store.pipeline import run
from knowledge_store.portal_api import handler, index
from knowledge_store.store import LocalStore, put_json
from test_lifecycle import DOCS, PROFILE

ROOT = Path(__file__).resolve().parents[1]


def test_every_module_the_stack_uses_exists_and_is_not_ignored():
    for tf in (ROOT / "infra").rglob("*.tf"):
        if ".terraform" in tf.parts:
            continue
        for src in re.findall(r'source\s*=\s*"(\.\.?/[^"]+)"', tf.read_text()):
            mod = (tf.parent / src).resolve()
            assert (mod / "main.tf").is_file(), f"{tf.relative_to(ROOT)} uses missing module {src}"
            ignored = subprocess.run(["git", "check-ignore", "-q", str(mod / "main.tf")], cwd=ROOT).returncode == 0
            assert not ignored, f"module {src} is gitignored, so a clone would not have it"


def test_portal_role_reads_collection_prefixes():
    tf = (ROOT / "infra/modules/portal/main.tf").read_text()
    assert "collections/*/${p}/*" in tf
    served = re.search(r"served_prefixes\s*=\s*\[([^\]]*)\]", tf).group(1)
    for layer in ("gold", "portal", "ontology", "config"):
        assert f'"{layer}"' in served


@pytest.fixture
def mixed(tmp_path, monkeypatch):
    """One collection with a public source and a private one; both mention the unknown Instrument."""
    root = LocalStore(tmp_path / "root")
    put_json(root, collections.CONFIG, [{"id": "m"}])
    for n, b in DOCS.items():
        root.put(f"landing/m/public/{n}", b.encode())
    root.put("landing/m/private/secret.md",
             b"# Secret\n\nMission Zeta was launched by Agency Nova in 2025. Mission Zeta carries Instrument Hush.")
    lake = collections.scoped(root, "m")
    put_json(lake, layout.CONFIG_SOURCES, [
        {"name": "public", "type": "s3_landing", "options": {"prefix": "landing/m/public/"}},
        {"name": "private", "type": "s3_landing", "options": {"prefix": "landing/m/private/"}, "scope": "private"}])
    put_json(lake, layout.CONFIG_SETTINGS, {"ontology_mode": "auto", "discovery_min_docs": 3, "discovery_resamples": 1})
    put_json(lake, layout.CONFIG_PROFILE, PROFILE.to_dict())
    run.run(root, FakeClient, "fake")
    monkeypatch.setattr(handler, "_lake", root)
    index._cache.clear()
    return root, lake


def _call(path, private, qs=None):
    groups = "[private-readers]" if private else "[]"
    ev = {"rawPath": path, "requestContext": {"http": {"method": "GET"},
          "authorizer": {"jwt": {"claims": {"sub": "u", "cognito:groups": groups}}}},
          "queryStringParameters": {"c": "m", **(qs or {})}}
    res = handler.handler(ev, None)
    return res["statusCode"], json.loads(res["body"])


def test_private_candidate_evidence_is_withheld(mixed):
    _, public = _call("/api/summary", private=False)
    _, private = _call("/api/summary", private=True)
    text = json.dumps(public["candidates"])
    assert "Instrument Hush" not in text and "Mission Zeta" not in text
    assert "Instrument Hush" in json.dumps(private["candidates"])
    inst = next(t for t in public["candidates"] if t["term"] == "Instrument")
    assert all(e["scope"] == "public" for e in inst["evidence"])


def test_private_entities_and_passages_are_withheld(mixed):
    _, found = _call("/api/entities", private=False, qs={"q": "Zeta"})
    assert found["total"] == 0
    _, found = _call("/api/entities", private=True, qs={"q": "Zeta"})
    assert found["total"] == 1


def test_drafts_are_for_curators(mixed):
    status, body = _call("/api/drafts", private=False)
    assert status == 403
    status, body = _call("/api/drafts", private=True)
    assert status == 200 and body["drafts"]
