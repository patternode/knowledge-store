"""Evaluation sets from YAML files."""

from __future__ import annotations

from pathlib import Path

from knowledge_store.evaluation.domain.sets import EvalSet, parse


def load(path: str | Path) -> EvalSet:
    import yaml
    p = Path(path)
    return parse(yaml.safe_load(p.read_text(encoding="utf-8")), name=p.stem)


def load_set(path: str | Path) -> EvalSet:
    """load, under the name the Evaluation contract publishes."""
    return load(path)
