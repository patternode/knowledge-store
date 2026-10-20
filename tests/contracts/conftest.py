"""One lake swept once with the fake model, shared by the context contract tests that need a
lake with documents, passages, an active ontology and a projection."""

from __future__ import annotations

import pytest

from fake_llm import FakeClient
from knowledge_store.apps import sweep
from knowledge_store.platform_services.adapters.store import LocalStore
from knowledge_store.platform_services.domain import layout
from knowledge_store.platform_services.ports import put_json
from knowledge_store.platform_services.slices import collections
from test_lifecycle import DOCS, PROFILE


@pytest.fixture(scope="session")
def swept(tmp_path_factory):
    root = LocalStore(tmp_path_factory.mktemp("contracts") / "lake")
    put_json(root, collections.CONFIG, [{"id": "m"}])
    for n, b in DOCS.items():
        root.put(f"landing/m/{n}", b.encode())
    lake = collections.scoped(root, "m")
    put_json(lake, layout.CONFIG_SOURCES, [{"name": "docs", "type": "s3_landing", "options": {"prefix": "landing/m/"}}])
    put_json(lake, layout.CONFIG_SETTINGS, {"ontology_mode": "auto", "discovery_min_docs": 3, "discovery_resamples": 1})
    put_json(lake, layout.CONFIG_PROFILE, PROFILE.to_dict())
    sweep.run(root, FakeClient, "fake")
    return lake
