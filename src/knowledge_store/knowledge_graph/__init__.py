"""BC-004 Knowledge graph: the record and its projections (the index, the SPARQL store, the optional graph backends, the passage index), and the read-only tools over them, filtered by scope.

This module is the context's contract: other contexts import only the names below.
"""

from knowledge_store.kernel.contract import lazy

_EXPORTS: dict[str, str] = {
    "FILTER": "slices.tools",
    "GraphStore": "ports",
    "Index": "adapters.index",
    "PassageSearch": "ports",
    "ReadModel": "ports",
    "SparqlStore": "ports",
    "TOOLS": "slices.tools",
    "describe": "slices.table_query",
    "describe_figure": "slices.table_query",
    "gateway": "@adapters.gateway",
    "index": "@adapters.index",
    "profile_text": "slices.tools",
    "run_tool": "slices.tools",
    "table_query": "@slices.table_query",
    "tool_config": "slices.tools",
    "traverse": "@domain.traverse",
    "values_equal": "slices.table_query",
    "vocabulary": "slices.tools",
}

__getattr__, __dir__ = lazy(__name__, _EXPORTS)
