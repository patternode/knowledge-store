"""BC-004 Knowledge graph: the record and its projections (the index, the SPARQL store, the optional graph backends, the passage index), and the read-only tools over them, filtered by scope.

This module is the context's contract: other contexts import only the names below.
"""

from knowledge_store.kernel.contract import lazy

_EXPORTS: dict[str, str] = {
}

__getattr__, __dir__ = lazy(__name__, _EXPORTS)
