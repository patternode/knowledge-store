"""Tunable settings: the limits and names a deployment sets through its environment.

Configuration is read in composition roots and adapters (ADR-046 point 7). The exception is a
small set of tunable numbers and names that domain rules are written against (the valves'
limits, the claim names a token carries, the default chat model). They are read here, and only
here, so the domain never touches the environment itself and a test can see every one of them.
"""

from __future__ import annotations

import os


def text(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def number(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def names(name: str, default: str) -> list[str]:
    """A comma-separated list."""
    return [n.strip() for n in os.environ.get(name, default).split(",") if n.strip()]
