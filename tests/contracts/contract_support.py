"""Helpers for context contract tests: each consumer names what it uses from a provider's contract."""

from __future__ import annotations

import importlib


def published(provider: str, names: list[str]) -> None:
    """Every name resolves through the provider's contract and is listed by it."""
    mod = importlib.import_module(f"knowledge_store.{provider}")
    listed = set(dir(mod))
    missing = [n for n in names if n not in listed]
    assert not missing, f"{provider} no longer publishes {missing}"
    for n in names:
        assert getattr(mod, n) is not None, f"{provider}.{n} resolves to None"
