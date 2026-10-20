"""A context's contract: the names other contexts may import, loaded only when first used.

Each bounded context's package `__init__` is its contract. It lists the names it publishes and
the module each lives in, and this helper resolves them on first access (PEP 562). Loading on
access keeps a context importable where its heavier dependencies are absent: the portal Lambda
ships with the standard library and boto3 only, and importing the Answering contract there must
not pull in rdflib. It also keeps package imports free of cycles, because naming a contract does
not import the modules behind it.
"""

from __future__ import annotations

import importlib


def lazy(package: str, exports: dict[str, str]):
    """`__getattr__` and `__dir__` for a contract package. exports maps a published name to the
    module (relative to the package) that defines it, or, with a leading @, to a module that is
    itself published (for a module of constants or helpers that callers use as a namespace)."""

    def __getattr__(name: str):
        mod = exports.get(name)
        if mod is None:
            raise AttributeError(f"module {package!r} publishes no {name!r}")
        if mod.startswith("@"):
            return importlib.import_module(f"{package}.{mod[1:]}")
        return getattr(importlib.import_module(f"{package}.{mod}"), name)

    def __dir__():
        return sorted(exports)

    return __getattr__, __dir__
